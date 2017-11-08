from typing import Iterable
from typing import List
from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
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
    https://docs.djangoproject.com/en/1.8/topics/db/managers/#custom-managers-and-model-inheritance

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
            if manager.use_proxy_model:
                concrete_model = manager._original_model
            else:
                concrete_model = manager._original_model._meta.concrete_model
                if concrete_model is None:
                    # we don't have a concrete model yet
                    return manager._original_model

            manager._concrete_model = concrete_model

        return manager._concrete_model

    def __set__(self, manager: Manager, model: Model):
        manager._original_model = model
        manager._concrete_model = None


class GenericUserProfileManager(BaseManager):
    """
    Polymorphic manager that uses user_to_profile() to
    """

    """ Set this in descendant classes to pass the proxy model rather than the concrete model to user_to_profile() """
    #use_proxy_model = False    # Until we've decided what the most common case is, this has to be set explicitly

    model = _DeferredResolveConcreteModel()

    def __init__(self) -> None:
        assert hasattr(self, 'use_proxy_model'), 'Must specify use_proxy_model on GenericUserProfileManager'

        # We have to jump through some hoops because the QuerySet creation is hardcoded in multiple
        # places in BaseManager -- eg _clone() -- so we can't simply add extra constructor params,
        # and the we don't even know what model we're going to be attached to until contribute_to_class()
        super().__init__()

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
        # Instead we have to dynamically create a new QuerySet class (this only happens once on model init)

        # Sanity check: if this doesn't pass then we're probably extending something that wasn't created
        # using BaseManager.from_queryset(); need extra tests to check that this works
        assert not isinstance(self._queryset_class, _GenericUserProfileQuerySet), \
            'GenericUserProfileQuerySet can only appear once in the ancestor list'

        assert hasattr(self, '_queryset_class')
        assert not hasattr(self._queryset_class, '_user_to_profile')

        # Only now do we know what queryset we're supposed to be extending
        class GenericUserProfileQuerySet(_GenericUserProfileQuerySet, self._queryset_class):

            user_to_profile = self.user_to_profile
            _original_model = model
            _use_proxy_model = self.use_proxy_model

            def __init__(self, model: Optional[Model] = None, *args, **kwargs) -> None:
                # We can't determine this at class construction time because _meta.concrete_model is not yet set
                # We also can't add any parameters to the constructor because self._clone() hardcodes the creation
                #  of a new queryset so we have to ensure that we only dereference the proxy model at most once
                # This will do the wrong thing if you use multiple inheritance from a GenericUserProfileManager; don't do that
                if not self._use_proxy_model and model._meta.proxy:
                    # # self._dereference_proxy_model = False
                    # if model._meta.proxy:
                    model = model._meta.concrete_model
                super().__init__(model=model, *args, **kwargs)
                self._iterable_class = _GenericUserProfileIterable

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
