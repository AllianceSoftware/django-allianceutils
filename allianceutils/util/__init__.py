from typing import Callable
from typing import Tuple

from .camelize import camel_to_underscore
from .camelize import camelize
from .camelize import underscore_to_camel
from .camelize import underscoreize
from .date import python_to_django_date_format

__all__ = [
    'camel_to_underscore',
    'camelize',
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

