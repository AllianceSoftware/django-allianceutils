import importlib
import json
import signal
import traceback

from django.db import connection
from django.db import transaction

from allianceutils.asynctask import AsyncTaskItem


class WorkerTimeoutException(Exception):
    pass


def signal_handler(*args, **kwargs):
    raise WorkerTimeoutException


signal.signal(signal.SIGALRM, signal_handler)


def decoratored_celery_shared_task(f):  # to allow for late importing
    from celery import shared_task
    return shared_task(f)


class CeleryQueue:
    def push(self, task):
        transaction.on_commit(lambda: CeleryQueue.run_func.delay(task.id))

    def validate(self, *args, **kwargs):
        return True

    @staticmethod
    @decoratored_celery_shared_task
    def run_func(task_id):

        with transaction.atomic():
            task = AsyncTaskItem.objects.select_for_update().get(id=task_id)
            status = task.get_status()
            if status in ["Processing", "Success"]:
                return
            task.mark_processing()

        try:
            p = importlib.import_module(task.task_module)
            p = getattr(p, task.task_class)

            if task.timeout:
                signal.alarm(task.timeout)

            result = p(*task.payload["args"], **task.payload["kwargs"]).__run__()
        except Exception:
            task.mark_failed(traceback.format_exc())
            # kick it back into the queue for another attempt if we're not hitting the max retry yet
            if task.get_retries() < task.max_retries:
                CeleryQueue.run_func.delay(task.id)
            # do we want to do some handling on the "final" failure?

        else:
            task.mark_success(result)

            # still mark as success, but throws an error:
            if result is None:
                raise ValueError(
                    f"run() of {task.task_module}.{task.task_class} returned None. This is not allowed; change it to return True."
                )
        finally:
            signal.alarm(0)


class SQSQueue:
    sqs = None
    queue_name = ""

    def __init__(self, **configurations):
        import boto3

        self.queue_name = configurations.pop("queue_name")
        self.sqs = boto3.resource("sqs", **configurations)
        self.queue = self.sqs.get_queue_by_name(self.queue_name)

    def validate(self, *args, **kwargs):
        if "MessageDeduplicationId" in kwargs:
            raise TypeError(
                "MessageDeduplicationId will be set automatically for SQS queues. Do not pass it manually."
            )
        if (
            kwargs and not "MessageBody" in kwargs
        ):  # if kwargs's empty, this'll most likely be a listener instance
            raise TypeError("MessageBody is expected to present in any SQS queue task.")
        return True

    def push(self, task):
        transaction.on_commit(
            lambda: self.queue.send_message(
                MessageDeduplicationId=str(task.id), **task.payload["kwargs"]
            )
        )

    def listen(self, **kwargs):
        while True:
            self.listen_once(**kwargs)

    def listen_once(self, **kwargs):
        recv_setting = {"MaxNumberOfMessages": 1, "WaitTimeSeconds": 20}
        recv_setting.update(kwargs)

        for message in self.queue.receive_messages(recv_setting):
            # Force django to open a new connection as required to avoid issues with connections
            # having been closed externally (eg. postgres server restart or other causes)
            connection.close()

            task_id = message.attributes.get("MessageDeduplicationId")

            with transaction.atomic():
                task, created = AsyncTaskItem.objects.select_for_update().get_or_create(
                    id=int(task_id)
                )  # in case of SQS we might have "outside" source of queues eg lambda
                if created and message.body:
                    task.payload = json.loads(
                        message.body
                    )  # message.body should always be a stringified json
                    task.save()

                status = task.get_status()
                if status in ["Processing", "Success"]:
                    return

                task.mark_processing()

            try:
                p = importlib.import_module(task.task_module)
                p = getattr(p, task.task_class)

                if task.timeout:
                    signal.alarm(task.timeout)

                result = p(message=message).__run__()
            except Exception:
                task.mark_failed(traceback.format_exc())
                # dont delete the message if retry maximum's not hit yet; this'll cause sqs queue to send it again next time
                if task.get_retries() >= task.max_retries:
                    message.delete()
            else:
                task.mark_success(result)

                # still mark as success, but throws an error:
                if result is None:
                    raise ValueError(
                        f"run() of {task.task_module}.{task.task_class} returned None. This is not allowed; change it to return True."
                    )
                message.delete()
            finally:
                signal.alarm(0)
