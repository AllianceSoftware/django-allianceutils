import functools
import inspect
from typing import Callable


class _CachedMethodDescriptor:
    fn: Callable
    cache_attr: str

    def __init__(self, fn: Callable):
        self.fn = fn
        self.cache_attr = f'_cache__{fn.__name__}'

    def __get__(self, obj, objtype):
        f = functools.partial(self.__call__, obj)
        f.clear_cache = functools.partial(self.clear_cache, obj)
        functools.update_wrapper(f, self.fn)
        return f

    def __call__(self, obj, *args, **kwargs):
        if not hasattr(obj, self.cache_attr):
            setattr(obj, self.cache_attr, self.fn(obj, *args, **kwargs))
        return getattr(obj, self.cache_attr)

    def clear_cache(self, obj):
        try:
            delattr(obj, self.cache_attr)
        except AttributeError as ae:
            # if obj is None then this was called on the class and not the
            # object instance
            if obj is None:
                raise AttributeError("clear_cache() should be called via a class instance, not a class") from ae


def method_cache(fn: Callable) -> Callable:
    """
    Method decorator to cache function results.

    Only works on methods with no parameters (other than self)

    Clear cache for MyObject.my_method with my_object.my_method.clear_cache()
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

    return _CachedMethodDescriptor(fn)
