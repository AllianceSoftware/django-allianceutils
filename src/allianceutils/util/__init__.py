from pathlib import Path
from typing import Callable
from typing import Iterable
from typing import Tuple
from typing import Union

from django.conf import settings
from django.utils.autoreload import autoreload_started
from django.utils.autoreload import StatReloader

from .camel_case import camel_to_underscore
from .camel_case import camelize
from .camel_case import underscore_to_camel
from .camel_case import underscoreize
from .date import python_to_django_date_format
from .get_firstparty_apps import get_firstparty_apps

__all__ = [
    'camel_to_underscore',
    'camelize',
    'get_firstparty_apps',
    'underscore_to_camel',
    'underscoreize',

    'python_to_django_date_format',

    'retry_fn',
]


def retry_fn(fn: Callable, allowable_exceptions: Tuple, retry_count: int=5):
    """
    Call fn, retrying if exception type in allowable_exceptions is raised up to retry_count times
    """
    for i in range(0, retry_count):
        try:
            return fn()
        except allowable_exceptions:
            if i == retry_count - 1:
                raise


def add_autoreload_extra_files(extra_files: Iterable[Union[str, Path]]):
    if not settings.DEBUG:
        return

    try:
       from werkzeug.serving import is_running_from_reloader
    except ImportError:
        is_running_from_reloader = None

    if is_running_from_reloader and is_running_from_reloader():
        # we're running from the main runserver_plus process
        if not hasattr(settings, 'RUNSERVER_PLUS_EXTRA_FILES'):
            settings.RUNSERVER_PLUS_EXTRA_FILES = []

        settings.RUNSERVER_PLUS_EXTRA_FILES += extra_files

    else:
        # either:
        #  - we're using the runserver (django) server
        #  - we're running from a child runserver_plus thread. If this is the case
        #    then the django autoreload signal will do nothing: working as intended

        def add_watched_files(sender: StatReloader, **kwargs):
            sender.extra_files.update([Path(p) for p in extra_files])

        autoreload_started.connect(add_watched_files)
