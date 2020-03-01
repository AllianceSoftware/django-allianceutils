
from django.conf import settings

from allianceutils.asynctask import AsyncTaskItem


class AsyncTask:
    max_retries = 3
    message = "Unnamed Task"
    timeout = 30  # Seconds. Set to 0 to allow infinity

    def __init__(self, *args, **kwargs):
        if not hasattr(settings, 'ASYNC_BACKEND'):
            raise ValueError('In order to use AsyncTask, you need to set ASYNC_BACKEND in your settings.')

        if not self.queue in settings.ASYNC_BACKEND:
            raise ValueError("Unknown Queue: %s" % self.queue)
        self.backend = settings.ASYNC_BACKEND[self.queue]
        self.args = args
        self.kwargs = kwargs
        self.backend.validate(*args, **kwargs)

    def enqueue(self):
        # local copy
        task = AsyncTaskItem(
            queue=self.queue,
            message=self.message,
            task_module=str(self.__module__),
            task_class=str(self.__class__.__name__),
            payload={"args": self.args, "kwargs": self.kwargs},
            max_retries=self.max_retries,
            timeout=self.timeout,
        )
        task.save()

        # remote copy
        self.backend.push(task)

    def run(self, *args, **kwargs):
        raise NotImplementedError

    def __run__(self):
        return self.run(*self.args, **self.kwargs)

    def listen(self, *args, **kwargs):
        # a generic AsyncTask class to be invoked by worker to start listening to dedicated queue.
        # note that this one creates other, Real instances of Task to actually perform the run.
        if not hasattr(self.backend, "listen"):
            raise NotImplementedError(
                "%s does not support manual listening" % self.queue
            )

        self.backend.listen(*args, **kwargs)

    def listen_once(self, *args, **kwargs):
        # just like listen, but runs only one time. can be used to emulate listen to multiple queues at the same time. BLOCKING.
        if not hasattr(self.backend, "listen_once"):
            raise NotImplementedError(
                "%s does not support manual one-time listening" % self.queue
            )

        self.backend.listen_once(*args, **kwargs)


def run_on_schedule(*args, **kwargs):
    # this decorator does not actually do anything by itself; it serves as a more visible/friendly
    # meta defintion for the task to be run.
    def ros_decorator(f):
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper
    return ros_decorator
