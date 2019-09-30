from collections import OrderedDict

from django.contrib.postgres.fields import JSONField
from django.db import models


class AsyncTaskStatusEnum:
    QUEUED = 1
    PROCESSING = 2
    SUCCEEDED = 3
    FAILED = 4

    choices = OrderedDict(
        (
            (QUEUED, "Queued"),
            (PROCESSING, "Processing"),
            (SUCCEEDED, "Succeeded"),
            (FAILED, "Failed"),
        )
    )


class AsyncTaskItem(models.Model):
    # name of the queue
    queue = models.CharField(blank=True, max_length=255)
    created_at = models.DateTimeField(auto_now=True)

    # human readable message
    message = models.CharField(blank=True, max_length=255)

    task_module = models.CharField(max_length=255)
    task_class = models.CharField(max_length=255)
    payload = JSONField(blank=True, null=True)

    # null means the task's not executed yet or has failed. a successful run() should never return None.
    success_result = JSONField(blank=True, null=True)

    # how many retries are allowed?
    max_retries = models.PositiveSmallIntegerField()

    # how long this task's allowed to run before it times out? - set to
    timeout = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "alliance_utils_async_task_item"

    def save(self):
        new = not self.id
        super().save()
        if new:
            AsyncTaskStatus(item=self, status=AsyncTaskStatusEnum.QUEUED).save()

    def get_status(self):
        return self.status.latest("created_at").status

    def get_retries(
        self
    ):  # how many times this task had been retried, inclusive if its currently undergoing a retry
        return self.status.filter(status=AsyncTaskStatusEnum.PROCESSING).count()

    def mark_processing(self):
        AsyncTaskStatus(item=self, status=AsyncTaskStatusEnum.PROCESSING).save()

    def mark_failed(self):
        AsyncTaskStatus(item=self, status=AsyncTaskStatusEnum.FAILED).save()

    def mark_success(self, result):
        AsyncTaskStatus(item=self, status=AsyncTaskStatusEnum.SUCCEEDED).save()
        self.success_result = result
        self.save()


class AsyncTaskStatus(models.Model):
    item = models.ForeignKey(
        AsyncTaskItem, on_delete=models.CASCADE, related_name="status"
    )
    status = models.PositiveSmallIntegerField(
        choices=AsyncTaskStatusEnum.choices.items()
    )
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "alliance_utils_async_task_status"

