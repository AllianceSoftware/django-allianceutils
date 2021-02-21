from typing import Iterable
from typing import Optional
from typing import Type
from typing import Union

from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import UserManager
from django.core import checks
from django.core.exceptions import ValidationError
from django.db.models import Manager
from django.db.models import Model
from django.db.models import QuerySet
from django.db.models.query import ModelIterable

from allianceutils.checks import ID_ERROR_PROFILE_RELATED_TABLES


class GenericUserProfileIterable(ModelIterable):
    """
    The iterator that transforms user records into profiles
    """
    def __iter__(self) -> Iterable[Model]:
        if self.queryset._do_iterate_profiles:
            for user in super().__iter__():
                yield user.profile
        else:
            yield from super().__iter__()


class GenericUserProfileQuerySet(QuerySet):
    """
    QuerySet that will iterate over user profiles if set_iterate_profiles() has been called
    """

    def __init__(self, *args, **kwargs):
        # We can't pass through _do_iterate_profiles as a constructor argument because QuerySet creation is hardcoded
        # in multiple places in BaseManager [eg _clone()]
        super().__init__(*args, **kwargs)
        self._do_iterate_profiles = False
        self._iterable_class = GenericUserProfileIterable

    def profiles(self) -> QuerySet:
        """
        Return a queryset that when iterated will yield User profiles instead of User records
        """
        qs = self.all()
        qs._do_iterate_profiles = True
        qs._validate_iterator()
        return qs

    def values(self, *args, **kwargs) -> QuerySet:
        # We want to fail early if needed rather than when the iterator is created (easier to debug)
        qs = super().values(*args, **kwargs)
        qs._validate_iterator()
        return qs

    def values_list(self, *args, **kwargs) -> QuerySet:
        # We want to fail early if needed rather than when the iterator is created (easier to debug)
        qs = super().values_list(*args, **kwargs)
        qs._validate_iterator()
        return qs

    def _validate_iterator(self):
        """
        We shouldn't use values() and values_list() in conjunction with profiles()

        (each dict would have different fields, would lead to subtle bugs)

        This might also be caused if _iterable_class is overwritten with something that
        does not extend GenericUserProfileIterable (also a dev mistake).

        This is not a hard restriction and is only intended to catch developer mistakes; this constraint may
        be relaxed in future when the need arises.
        """
        if self._do_iterate_profiles and not issubclass(self._iterable_class, GenericUserProfileIterable):
            raise ValueError('Bad _iterable_class. (Trying to use values()/values_list() with profiles()? This has not been implemented yet)')

    def _clone(self, **kwargs):
        qs = super()._clone(**kwargs)
        qs._do_iterate_profiles = self._do_iterate_profiles
        return qs

    def _get_related_profile_tables(self):
        if _is_profile(self.model):
            return []
        else:
            return self.model.related_profile_tables

    def select_related_profiles(self) -> QuerySet:
        """
        Adds relevant select_related() joins so that user_to_profile() doesn't trigger extra queries
        """
        if _is_profile(self.model):
            # is already a profile table so no need to do any joins
            return self._clone()
        return self.select_related(*self.model.related_profile_tables)

    def prefetch_related_profiles(self) -> QuerySet:
        """
        Adds relevant select_related() joins so that user_to_profile() doesn't trigger extra queries
        """
        if _is_profile(self.model):
            # is already a profile table so no need to do any joins
            return self._clone()
        return self.prefetch_related(*self.model.related_profile_tables)

    def iterator(self):
        # extra validation check in case some subclass overwrote our other validation checks
        self._validate_iterator()
        return super().iterator()


def _is_profile(model: Type[Model]) -> bool:
    """
    Is model a profile model?

    Assumes model is one of either User or a UserProfile model
    """

    # This will work for the common User/UserProfile pattern but
    # won't be correct if we have 3 or more levels of multi-table-inheritance
    return bool(model._meta.parents)


# Concrete models with a GenericUserProfileManagerMixin must define related_profile_tables
def _validate_related_profile_tables(model: Type[Model], manager_name: str):
    # , model_app_name: Tuple[str, str],
    # app_name, model_name = model_app_name
    # app_name, model_name = model._meta.app_label, model._meta.model_name
    # print('validating %s.%s' % (app_name, model_name))
    if not getattr(model, 'related_profile_tables', None):
        msg = 'A model with a GenericUserProfileManagerMixin (%s.%s) is missing a related_profile_tables definition' % \
              (model.__name__, manager_name)
        raise NotImplementedError(msg)


class GenericUserProfileManagerMixin(BaseUserManager):
    """
    Manager mixin that provides for iteration over user profiles.
    Is assumed to be a manager for a GenericUserProfile
    """
    _queryset_class = GenericUserProfileQuerySet

    def __init__(self, select_related_profiles=False, prefetch_related_profiles=False, *args, **kwargs):
        """
        Constructor; allows you to create a manager that will iterate over profiles by default

        :param select_related_profiles: If set, will automatically call select_related_profiles() and profiles() on every queryset
        :param prefetch_related_profiles: If set, will automatically prefetch_related_profiles() and profiles() on every queryset
        """
        self._auto_select_related_profiles = select_related_profiles
        self._auto_prefetch_related_profiles = prefetch_related_profiles

        if self._auto_select_related_profiles and self._auto_prefetch_related_profiles:
            # If you do this you probably messed up (is redundant and inefficient)
            raise ValueError('Both prefetching and selecting related entities is usually a mistake')

        super().__init__(*args, **kwargs)

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        if not isinstance(qs, GenericUserProfileQuerySet):
            raise TypeError('GenericUserProfileManagerMixin QuerySet does not inherit GenericUserProfileQuerySet')
        if self._auto_select_related_profiles:
            qs = qs.select_related_profiles()
        if self._auto_prefetch_related_profiles:
            qs = qs.prefetch_related_profiles()
        if self._auto_prefetch_related_profiles or self._auto_select_related_profiles:
            qs = qs.profiles()
        return qs

    def contribute_to_class(self, model: Model, name):
        # Do some extra sanity checks on the model
        #
        # We could extend the underlying queryset class and mix in GenericUserProfileQuerySet automatically here
        # but that involves extra hidden magic which is anti-pythonic

        # If get_queryset() does something other than instantiating _queryset_class then this may be a false positive
        # but that's a case we haven't had to handle yet
        if not issubclass(self._queryset_class, GenericUserProfileQuerySet):
            raise TypeError('GenericUserProfileManagerMixin._queryset_class must extend GenericUserProfileQuerySet')

        super(GenericUserProfileManagerMixin, self).contribute_to_class(model, name)

    def check(self, **kwargs):
        errors = super().check(**kwargs)

        model = self.model
        if getattr(model, 'related_profile_tables') is None:
            errors.append(checks.Error(
                "Model '%s' does not define related_profile_tables" % model._meta.label,
                hint="Manager '%s' needs related_profile_tables" % self.name,
                obj=self.model,
                id=ID_ERROR_PROFILE_RELATED_TABLES,
            ))

        return errors

    def profiles(self) -> QuerySet:
        return self.get_queryset().profiles()

    # TODO: It would be nice to be able to do something like:
    #   SomeModel.objects.select_related('user__profile')
    # and have the '__profile' transformed into the relevant select_related() based on model.related_profile_tables
    # unfortunately the code to do the joins is baked into SQLCompiler.get_related_selections() and is not really
    # extensible without being very invasive
    #
    # Instead we have to call select_related_profiles on an unrelated queryset with a prefix

    def select_related_profiles(self, queryset: Optional[Union[QuerySet, Manager]]=None, prefix: str='') -> QuerySet:
        if bool(queryset) != bool(prefix):
            raise ValueError('Either none or both of queryset and prefix must be specified')

        if not queryset and not prefix:
            return self.get_queryset().select_related_profiles()
        else:
            return queryset.select_related(*[prefix + '__' + profile for profile in self.model.related_profile_tables])

    def prefetch_related_profiles(self, queryset: Optional[Union[QuerySet, Manager]]=None, prefix: str='') -> QuerySet:
        if bool(queryset) != bool(prefix):
            raise ValueError('Either none or both of queryset and prefix must be specified')

        if not queryset and not prefix:
            return self.get_queryset().prefetch_related_profiles()
        else:
            return queryset.prefetch_related(*[prefix + '__' + profile for profile in self.model.related_profile_tables])


class GenericUserProfileManager(GenericUserProfileManagerMixin, UserManager):
    """
    Default User Profile Manager using django.contrib.auth.models.UserManager
    """
    pass


class GenericUserProfile(Model):
    """
    A User model that provides iteration over user profiles (if available)
    You should override related_profile_tables
    """
    objects = GenericUserProfileManager()
    profiles = GenericUserProfileManager(select_related_profiles=True)

    class Meta:
        abstract = True

    @classmethod
    def normalize_email(cls, email):
        return email.lower()

    def clean(self):
        if self.__class__._base_manager.filter(email=self.__class__.normalize_email(self.email)).exclude(pk=self.pk).exists():
            raise ValidationError({'email': 'Sorry, this email address is not available.'})

    def save(self, *args, **kwargs):
        self.email = GenericUserProfile.normalize_email(self.email)
        return super().save(*args, **kwargs)

    def get_profile(self) -> Model:
        # We're already a profile
        if _is_profile(self):
            return self

        # try each FK reference one at a time; this will be inefficient if
        # select_related_profiles() or prefetch_related_profiles() haven't been called
        for profile_model in self.related_profile_tables:
            try:
                return getattr(self, profile_model)
            except AttributeError:
                pass

        # Nothing matches; this is a user record without a profile
        return self

    class _CachedProfileDescriptor:
        """
        Evaluates and caches the result of get_profile()
        Caches the result on all records in the multi-table inheritance chain
        """
        def __get__(self, obj, cls=None) -> Optional[Model]:
            if obj is None:
                return self

            user_profile = obj.get_profile()

            # cache the result on all records in the multi-table inheritance chain
            record = user_profile
            while isinstance(record, Model):
                record.__dict__['profile'] = user_profile

                # note that record.pk will always return the underlying pk id, not the user_ptr record
                record = getattr(record, record._meta.pk.name)

            return user_profile

    profile = _CachedProfileDescriptor()

    # This should be overridden to include a list of the tables to join to [will be passed to select_related()]
    related_profile_tables = None
