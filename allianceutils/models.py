from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Manager
from django.db.models import Model
from django.db.models import QuerySet


def combine_querysets_as_manager(*queryset_classes: List[QuerySet]) -> Manager:
    """
    Replacement for django_permanent.managers.MultiPassThroughManager which no longer works in django 1.8

    Returns a new Manager instance that passes through calls to multiple underlying queryset_classes via inheritance

    :param queryset_classes: Queryset cla
    :return: class
    """
    name = "".join([cls.__name__ for cls in queryset_classes])
    return type(name, queryset_classes, {}).as_manager()


class NoDeleteQuerySet(QuerySet):
    def delete(self, force: bool=False):
        raise IntegrityError(f"Instances of model '{self.__class__.__name__}' are marked as undeletable")


class NoDeleteModel(Model):
    """
    A model that cannot be deleted.

    Note that this is an abstract Model, please read
    https://docs.djangoproject.com/en/stable/topics/db/managers/#custom-managers-and-model-inheritance

    If you wish to override the default manager, you need to combine the queryset like so:

    class MyModel(NoDeleteModel):
        objects = combine_querysets_as_manager(NoDeleteQuerySet, MyQuerySet)

    If you do not do this then individual record deletions will be blocked, but not deletions via a queryset
    """
    objects = Manager.from_queryset(NoDeleteQuerySet)

    def delete(self, *args, **kwargs):
        raise IntegrityError(f"Instances of model '{self.__class__.__name__}' are marked as undeletable")

    class Meta:
        abstract = True


# -------------------------------------------------------------------------------------------------------------------

# We need a placeholder to indicate that a ValidationError actually has no error; we use this
class _NO_VALIDATION_ERROR:
    pass


class _ExtendedValidationError(ValidationError):
    """
    Extended version of ValidationError for use with raise_validation_errors()

    Internal behaviour is slightly different in that it may contain no errors at all
    """

    ErrorType = Union[str, ValidationError]

    def add_error(self, field: Optional[str], error: Union[ErrorType, List[ErrorType], Dict[str, List[ErrorType]]]):
        """
        This has the same behaviour as BaseForm.add_error()
        """
        if not isinstance(error, ValidationError):
            # Normalize to ValidationError and let its constructor
            # do the hard work of making sense of the input.
            error = _ExtendedValidationError(error)

        if hasattr(error, 'error_dict'):
            if field is not None:
                raise TypeError(
                    "The argument `field` must be `None` when the `error` "
                    "argument contains errors for multiple fields."
                )

        if field is not None:
            error = _ExtendedValidationError({field: error})

        self.merge(error)

    def merge(self, error: ValidationError):
        """
        Merge another ValidationError into this one
        """

        # we need to copy self in order to avoid recursive self-references
        self_copy = _ExtendedValidationError(self)
        new_ve = self_copy.merged(error)

        # now copy the details from the new ValidationError into this one
        self.__dict__.clear()
        self.__dict__.update(new_ve.__dict__)

    def merged(self, errors: ValidationError) -> ValidationError:
        """
        Return a new ValidationError that is a merge of `self` and `errors`
        """

        def is_empty(ve):
            # ve might be a ValidationError instead of an _ExtendedValidationError
            # this does a little unbound function magic to treat it as though
            # it were an _ExtendedValidationError
            return _ExtendedValidationError._is_empty(ve)

        # A ValidationError could be in any of the following forms:
        # [1] dict: self.error_dict exists
        # [2] list: self.error_list exists but self.message doesn't
        # [3] scalar: self.message is a single message

        # list of validation errors to merge
        to_merge = [self, errors]

        # we need to promote one or more both to a dict-type ValidationError
        if any(hasattr(ve, 'error_dict') for ve in to_merge):
            to_merge_dicts = []
            for ve in to_merge:
                if not hasattr(ve, 'error_dict'):
                    ve_list = [x for x in ve.error_list if not is_empty(x)]
                    if ve_list:
                        to_merge_dicts.append({NON_FIELD_ERRORS: ve_list})
                else:
                    to_merge_dicts.append(ve.error_dict)

            merged_dict = {}
            for to_merge_dict in to_merge_dicts:
                for key, value in to_merge_dict.items():
                    merged_dict.setdefault(key, [])
                    merged_dict[key].extend(value.copy())

            new_ve = _ExtendedValidationError(merged_dict)
        else:
            codes = []
            params = []
            to_merge_messages = []
            to_merge_lists = []
            for ve in to_merge:
                if hasattr(ve, 'message'):
                    # ve might be a ValidationError instead of an _ExtendedValidationError
                    if not is_empty(ve):
                        to_merge_messages.append(ve.message)
                        to_merge_lists.extend(ve.error_list)
                        codes.append(ve.code)
                        params.append(ve.params)
                else:
                    to_merge_lists.extend(ve.error_list)

            if len(to_merge_lists) == 0:
                # all _NO_VALIDATION_ERROR
                new_ve = _ExtendedValidationError(_NO_VALIDATION_ERROR)
            elif len(to_merge_lists) == 1 and len(to_merge_messages) == 1:
                # was just a single ValidationError with a simple message
                new_ve = _ExtendedValidationError(to_merge_messages[0], code=codes[0], params=params[0])
            else:
                new_ve = _ExtendedValidationError(to_merge_lists)

        return new_ve

    def _is_empty(self) -> bool:
        """
        Does this actually have any validation errors recorded?

        The following are not considered errors:
        - a named field whose errors consist of an empty list
        - a non-truthy value in a list of errors
        - a ValidationError that is just an empty message

        For example, the following are considered empty validation errors:

        ValidationError(None)
        ValidationError('')
        ValidationError([''])
        ValidationError({})
        ValidationError({'my_field': []})

        The following *will* be considered validation errors:
        ValidationError({'my_field': ['']})
        ValidationError({'my_field': [None]})
        ValidationError('foo')
        ValidationError(['foo'])
        """
        return getattr(self, 'message', None) == _NO_VALIDATION_ERROR

    def capture_validation_error(self) -> '_ExtendedValidationErrorCaptureContext':
        return _ExtendedValidationErrorCaptureContext(self)


class _ExtendedValidationErrorCaptureContext:
    def __init__(self, ve: _ExtendedValidationError):
        self.ve = ve

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, ValidationError):
            self.ve.merge(exc_val)
            return True


class raise_validation_errors:
    def __init__(self, func: Optional[Callable]=None):
        if func is not None and not callable(func):
            raise TypeError('raise_validation_errors func is not callable')
        self.func = func

    def __enter__(self) -> _ExtendedValidationError:
        try:
            if self.func is not None:
                self.func()
            self.ve = _ExtendedValidationError(_NO_VALIDATION_ERROR)
        except ValidationError as ve:
            self.ve = _ExtendedValidationError(ve)

        return self.ve

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            if not self.ve._is_empty():
                raise self.ve

# -------------------------------------------------------------------------------------------------------------------
