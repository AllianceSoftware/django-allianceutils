import functools
import inspect
from typing import Callable
from typing import cast
from typing import Generic
from typing import TypeVar

ParamT = TypeVar("ParamT")
ReturnT = TypeVar("ReturnT")


class _CachedMethodDescriptor:
    fn: Callable
    cache_attr: str

    def __init__(self, fn: Callable):
        self.fn = fn
        self.cache_attr = f'_cache__{fn.__name__}'

    def __get__(self, obj, objtype):
        f = functools.partial(self.__call__, obj)
        # we dynamically attached the clear_cache method
        f.clear_cache = functools.partial(self.clear_cache, obj)  # type:ignore[attr-defined]
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


# see PEP612 for typing of decorators; this is additionally complicated by the fact that our decorator actually
# replaces the function with a descriptor.
#
# However in our case:
#   - from the perspective of the caller this should just look like the function is unchanged.
#   - we only accept methods that take no params (other than self)
#
# We can then simplify what's really going on behind the scenes and pretend that the function signature hasn't
# changed at all (except for the addition of the .clear_cache() method)
#
class DecoratedFuncWithClear(Generic[ReturnT]):
    def __call__(self) -> ReturnT:  # type:ignore[empty-body]  # this is just a stub for typing
        ...

    def clear_cache(self):
        ...


def method_cache(fn: Callable[[ParamT], ReturnT]) -> DecoratedFuncWithClear[ReturnT]:
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

    return cast(DecoratedFuncWithClear[ReturnT], _CachedMethodDescriptor(fn))
