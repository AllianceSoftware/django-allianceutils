from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Union

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Manager
from django.db.models import Model
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models.manager import BaseManager
from django.db.models.query import ModelIterable


def add_group_permissions(group_id: int, codenames: List[str]):
    """
    Add permissions to a group

    Assumes permissions with codenames already exist
    """
    group = Group.objects.get(pk=group_id)

    permissions = list(Permission.objects.filter(codename__in=codenames))

    # Check that the permissions actually exist
    missing = set(codenames) - set(p.codename for p in permissions)
    if len(missing):
        raise Permission.DoesNotExist(list(missing)[0])

    group.permissions.add(*permissions)


def get_users_with_permission(permission):
    return get_users_with_permissions((permission,))


def get_users_with_permissions(permissions: List[str]) -> Iterable[Model]:
    """
    Retrieves all users with specified static permissions (via a group or directly assigned)
    """
    query = Q(False)
    for permission in permissions:
        (app_label, codename) = permission.split('.', 1)
        query = query | Q(codename=codename, app_label=app_label)
    permissions = Permission.objects.filter(Q).values('pk')
    User = get_user_model()
    users = User.objects.filter(
        Q(user_permissions__pk__in=permissions) |
        Q(user__groups__permissions__pk__in=permissions)
    ).distinct()
    return users


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
        raise IntegrityError("Instances of model '%s' are marked as undeletable" % self.__class__.__name__)


class NoDeleteModel(Model):
    """
    A model that cannot be deleted.

    Note that this is an abstract Model, please read
    https://docs.djangoproject.com/en/1.11/topics/db/managers/#custom-managers-and-model-inheritance

    If you wish to override the default manager, you need to combine the queryset like so:

    class MyModel(NoDeleteModel):
        objects = combine_querysets_as_manager(NoDeleteQuerySet, MyQuerySet)

    If you do not do this then individual record deletions will be blocked, but not deletions via a queryset
    """
    objects = Manager.from_queryset(NoDeleteQuerySet)

    def delete(self, *args, **kwargs):
        raise IntegrityError("Instances of model '%s' are marked as undeletable" % self.__class__.__name__)

    class Meta:
        abstract = True


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


# ---------------------------------------------------------------------------------------------------------------------


class _GenericUserProfileIterable(ModelIterable):
    """
    The iterator that transforms user records into profiles
    """
    def __iter__(self) -> Iterable[Model]:
        for user in super().__iter__():
            yield self.queryset.user_to_profile(user)


class _GenericUserProfileQuerySet(object):
    """
    This is used to protect against GenericUserProfileQuerySet appearing multiple times in the queryset ancestor list
    """
    pass


class _DeferredResolveConcreteModel(object):
    """
    When model Managers are initialised there is no way to know whether a model is a proxy or not;
    this returns the concrete model when it becomes available
    """
    def __get__(self, manager: Manager, cls: type=None) -> Manager:
        if manager._concrete_model is None:
            manager._concrete_model = manager._original_model
        return manager._concrete_model

    def __set__(self, manager: Manager, model: Model):
        manager._original_model = model
        manager._concrete_model = None


class GenericUserProfileManager(BaseManager):
    """
    Polymorphic manager that uses user_to_profile() to
    """

    """ Set this in descendant classes to pass the proxy model rather than the concrete model to user_to_profile() """
    model = _DeferredResolveConcreteModel()

    def __init__(self) -> None:
        # We have to jump through some hoops because the QuerySet creation is hardcoded in multiple
        # places in BaseManager -- eg _clone() -- so we can't simply add extra constructor params,
        # and the we don't even know what model we're going to be attached to until contribute_to_class()
        super().__init__()

        # wipe the default queryset class to make sure it's not used before
        # contribute_to_class() sets it to the class we actually want
        self._original_queryset_class = self._queryset_class
        self._queryset_class = None

    def get_queryset(self, *args, **kwargs) -> QuerySet:
        qs = super().get_queryset(*args, **kwargs)
        return self.select_related_profiles(qs)

    def contribute_to_class(self, model: Model, name):
        # It is only now that we can know what model we were attached to and what QuerySet we should extend
        #
        # We can't use multiple inheritance because we get the error:
        #   Error when calling the metaclass bases metaclass conflict: the metaclass of a derived class
        #   must be a (non-strict) subclass of the metaclasses of all its bases
        #
        # Instead we have to dynamically create a new QuerySet class (this happens once at Model class creation)

        # Sanity check: if this doesn't pass then we're probably extending something that wasn't created
        # using BaseManager.from_queryset(); need extra tests to check that this works
        assert not isinstance(self._queryset_class, _GenericUserProfileQuerySet), \
            'GenericUserProfileQuerySet can only appear once in the ancestor list'

        assert hasattr(self, '_queryset_class')
        assert not hasattr(self._queryset_class, '_user_to_profile')

        # Only now do we know what queryset we're supposed to be extending
        class GenericUserProfileQuerySet(_GenericUserProfileQuerySet, self._original_queryset_class):

            user_to_profile = self.user_to_profile
            _original_model = model

            def __init__(self, model: Optional[Model] = None, *args, **kwargs) -> None:
                # We can't determine this at class construction time because _meta.concrete_model is not yet set
                # We also can't add any parameters to the constructor because self._clone() hardcodes the creation
                #  of a new queryset so we have to ensure that we only dereference the proxy model at most once
                # This will do the wrong thing if you use multiple inheritance from a GenericUserProfileManager; don't do that
                super().__init__(model=model, *args, **kwargs)
                self._iterable_class = _GenericUserProfileIterable

        # Replace the normal _queryset_class with a new one
        self._queryset_class = GenericUserProfileQuerySet

        super().contribute_to_class(model, name)

    @classmethod
    def user_to_profile(cls, user: Model) -> Model:
        """
        Takes a User record and returns the relevant associated Profile object
        """
        raise NotImplementedError('GenericUserProfileManagers need to implement user_to_profile()')

    @classmethod
    def select_related_profiles(cls, queryset: QuerySet) -> QuerySet:
        """
        Takes a queryset and adds select_related() to that user_to_profile() doens't trigger extra queries
        """
        raise NotImplementedError('GenericUserProfileManagers need to implement select_related_profiles()')
