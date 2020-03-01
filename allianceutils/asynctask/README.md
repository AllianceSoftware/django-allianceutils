# AsyncTask

A universal async task / queue module designed to handle async actions and cron tasks for you, deployable on heroku, shared hosting and dedicated VMs.

Common use case scenarios include sending email without blocking response, perform fetch of external data sources at scheduled time,
perform resource intense calculations, generate files in non-web format for download etc.

* [Installation](#installation)
* [Setup](#setup)
* [Usage](#usage)
    * [Task](#task)
    * [Cron](#cron)
* [Queue Backends](#queue-backends)

## Installation

* `pip install -e git+https://gitlab.alliancesoftware.com.au/alliance/alliance-django-utils.git@master#egg=allianceutils`
* Add `allianceutils.asynctask` to `INSTALLED_APPS`
* celery / boto3 will also need to be pre-installed for celery/SQS backend respectively.
* `asynctask` uses postgres' JSONField so this **requires postgres** 

## Setup

Config settings such as this one need to be added to settings/base.py.

```
ASYNC_BACKEND = {
    "celery-queue": CeleryQueue(),
    "sqs-queue": SQSQueue(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_SQS_REGION,
        queue_name="sqs_low_priority",
    ),
}
```

Multiple queues can be added even with same queue backend (subject to queue handler support), for the purpose of giving each queue a different
priority level.

If cronjob mode is desired, the management command `run_scheduled_jobs` needs to be added to your cron / dedicated worker.

## Usage

### Task

Once it's all setup, simply create Tasks as:

```

class CeleryTask(AsyncTask):
    queue = "celery-queue"
    message = "Add a, b, and c"
    timeout = 1

    def run(self, a, b, c):
        import time
        time.sleep(5) # emulate a slow action
        return a + b + c
```

and "run" it as
```
CeleryTask(1, c=2, b=3).enqueue()
```

This "run" will not be blocking, and the actual action would be handled asynchronously.

SQS Queue works in a similar fashion with a slightly different interface, due to message packing in SQS:
```
class SQSTask(AsyncTask):
    queue = "sqs-queue"
    message = "Add a, b, and c, too"

    def run(self, message):
        body = json.loads(message.body)
        return body["a"] + body["b"] + body["c"]

SQSTask(a=1, c=2, b=3).enqueue() # web
SQSTask().listen({"WaitTimeSeconds": 5}) # worker
```

* You can specify timeout and max_retries for any AsyncTask. They have a default value of 30 (seconds) and 3; set timeout to 0 to allow for infinite length tasks.
    * Tasks not completed in <timeout> seconds will be terminated and marked as fail. Failed tasks will be retried the next time it gets popped out from the queue, until max_retries threshold is hit.

* You can check the status of any task by accessing Task.get_status(); if a task is successfully completed, any return value will also be stored in Task.success_result

### Cron

* Use `@run_on_schedule(minute=3)` decorator to schedule Tasks.

```
@run_on_schedule(minute=3)
class CeleryScheduledTask(AsyncTask):
    queue = "celery-queue"
    message = "schedule task w/ empty constructor"

    def stuff(self):
        print("sending email..")
        import time
        time.sleep(3)
        print("email sent")

    def run(self):
        # NOTE: its the responsibility of these individual tasks to decide whether they want to block worker or not (instead of scheduler)
        # because all scheduler does is essentially insert these tasks into respective queues.
        import threading

        threading.Thread(target=self.stuff).start()
        return True
```

* Arguments on the decorator is similar to that of a linux `cron`: set `minute=3` and it'll run whenever the minute component of system time is 3. All datetime attributes can be used as an argument (
common ones are `minute`, `hour`, `day`, `weekday` and `month`)

## Queue Backends

AsyncTask module comes prebuilt with two queue handlers (see asynctask/backends.py), for Celery and Amazon SQS respectively.
It's possible to use other queues; all you need to do is implement a Queue class with minimal push() and validate() logic, and some internal way to
execute directions once they're popped out from the queue.

