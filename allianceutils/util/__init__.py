from typing import Callable
from typing import Tuple

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
