from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.db import models
from django.db.models import Q
from django.db.models.manager import BaseManager
from django.db.models.query import ModelIterable


def add_group_permissions(group_id, codenames):
    """
    Add permissions to a group

    :param group_id: group to add permissions to
    :param codenames: sequence of permission codenames (assumed permission already exists)
    :param allow_duplicates: Whether to throw an error if duplicate permissions assigned (defaults to false)
    :return:
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


def get_users_with_permissions(permissions):
    """
    Assumes authtools is the user model, grabs all users with specified static permissions
    :param permissions: permissions codenames to check
    :return: queryset of users with any of the listed permissions (via a group or directly)
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


def combine_querysets_as_manager(*queryset_classes):
    """
    Replacement for django_permanent.managers.MultiPassThroughManager which no longer works in django 1.8

    Returns a new Manager instance that passes through calls to multiple underlying queryset_classes via inheritance

    :param queryset_classes: Queryset cla
    :return: class
    """
    name = "".join([cls.__name__ for cls in queryset_classes])
    return type(name, queryset_classes, {}).as_manager()


class NoDeleteQuerySet(models.QuerySet):
    def delete(self, force=False):
        raise IntegrityError("Instances of model '%s' are marked as undeletable" % self.__class__.__name__)


class NoDeleteModel(models.Model):
    """
    A model that cannot be deleted.

    Note that this is an abstract Model, please read
    https://docs.djangoproject.com/en/1.8/topics/db/managers/#custom-managers-and-model-inheritance

    If you wish to override the default manager, you need to combine the queryset like so:

    class MyModel(NoDeleteModel):
        objects = combine_querysets_as_manager(NoDeleteQuerySet, MyQuerySet)

    If you do not do this then individual record deletions will be blocked, but not deletions via a queryset
    """
    objects = models.Manager.from_queryset(NoDeleteQuerySet)

    def delete(self, *args, **kwargs):
        raise IntegrityError("Instances of model '%s' are marked as undeletable" % self.__class__.__name__)

    class Meta:
        abstract = True

# ---------------------------------------------------------------------------------------------------------------------


class _GenericUserProfileIterable(ModelIterable):
    def __iter__(self):
        for user in super().__iter__():
            yield self.queryset.user_to_profile(user)


class _GenericUserProfileQuerySet(models.QuerySet):
    def __init__(self,
            full_init=False,
            dereference_proxy_model=False,
            model=None,
            user_to_profile=None,
            *args,
            **kwargs):
        if full_init:
            self.user_to_profile = user_to_profile
            if dereference_proxy_model and model._meta.proxy:
                model = model._meta.concrete_model
        super().__init__(model=model, *args, **kwargs)
        self._iterable_class = _GenericUserProfileIterable

    def _clone(self, **kwargs):
        clone = super()._clone(**kwargs)
        clone.user_to_profile = self.user_to_profile
        return clone


class GenericUserProfileManager(BaseManager.from_queryset(_GenericUserProfileQuerySet)):
    """
    Polymorphic manager that uses user_to_profile() to

    """

    # Implementation is complicated because a manager doesn't know at the time of definition (or even at construction)
    # what model it is going to be part of

    """ Set this in descendant classes to pass the proxy model rather than the concrete model to user_to_profile() """
    use_proxy_model = False

    def __init__(self, *args, **kwargs):
        # We have to jump through some hoops because the QuerySet creation is hardcoded in multiple
        # places in BaseManager -- eg _clone() -- so we can't simply add extra constructor params
        def queryset_construct(*args, **kwargs):
            return _GenericUserProfileQuerySet(
                full_init=True,
                dereference_proxy_model=not self.use_proxy_model,
                user_to_profile = self.user_to_profile,
                *args,
                **kwargs
            )
        self._queryset_class = queryset_construct
        super().__init__(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        return self.select_related_profiles(qs)

    @classmethod
    def user_to_profile(cls, user):
        """
        Takes a User record and returns the relevant associated Profile object
        """
        raise NotImplementedError('GenericUserProfileManagers need to implement user_to_profile()')

    @classmethod
    def select_related_profiles(cls, queryset):
        """
        Takes a queryset and adds select_related() to that user_to_profile() doens't trigger extra queries
        """
        raise NotImplementedError('GenericUserProfileManagers need to implement select_related_profiles()')
