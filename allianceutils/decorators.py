import functools
import inspect
from typing import Callable

from django.contrib.admin.views.decorators import staff_member_required as original_staff_member_required
from django.contrib.auth import REDIRECT_FIELD_NAME


# dont redirect to admin:login which breaks if admin's not present - redirect to generic login instead (which None will do).
def staff_member_required(view_func=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    return original_staff_member_required(view_func, redirect_field_name, login_url)


def method_cache(fn: Callable) -> Callable:
    """
    Method decorator to cache function results.

    Only works on methods with no parameters (other than self)

    Clear cache for MyObject.my_method with my_object.my_method(_cache=False)
    """
    if isinstance(fn, (staticmethod, classmethod)):
        # if staticmethod or classmethod then inspect.signature() fails even trying to introspect the function
        raise AssertionError("method_cache only works with regular methods with no parameters")
    else:
        sig = inspect.signature(fn)
        assert len(sig.parameters) == 1, "method_cache only works with regular methods with no parameters"
        # there's no way to tell the difference between a function and a method because a method is just
        # a regular function that gets bound when accessing it through a class, but if the first argument is
        # "self" we'll assume it's a method
        assert "self" in sig.parameters, "method_cache works on methods, not functions"

    cache_attr = f"_cache_{fn.__name__}"

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        if "_from_cache" in kwargs:
            if not kwargs["_from_cache"]:
                delattr(self, cache_attr)
            del kwargs["_from_cache"]
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, fn(self))
        return getattr(self, cache_attr)

    return wrapper
