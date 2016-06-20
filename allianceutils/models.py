from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.db import models
from django.db.models import Q


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
