from __future__ import annotations

from typing import Iterable
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union
from typing import cast

from allianceutils.checks import ID_ERROR_PROFILE_RELATED_TABLES
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import UserManager
from django.core import checks
from django.db.models import Model
from django.db.models import QuerySet
from django.db.models.query import ModelIterable
from typing_extensions import Self

_ModelT = TypeVar("_ModelT", bound=Model, covariant=True)


class GenericUserProfileIterable(ModelIterable):
    """
    The iterator that transforms user records into profiles
    """

    queryset: GenericUserProfileQuerySet  # this is coupled to this QuerySet

    def __iter__(self) -> Iterable[Union[GenericUserProfile, _ModelT]]:  # type:ignore[override]  # specialised return
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

    def profiles(self) -> Self:
        """
        Return a queryset that when iterated will yield User profiles instead of User records
        """
        qs = self.all()
        qs._do_iterate_profiles = True
        qs._validate_iterator()
        return qs

    def values(self, *args, **kwargs) -> Self:
        # We want to fail early if needed rather than when the iterator is created (easier to debug)
        qs = cast(Self, super().values(*args, **kwargs))
        qs._validate_iterator()
        return qs

    def values_list(self, *args, **kwargs) -> Self:
        # We want to fail early if needed rather than when the iterator is created (easier to debug)
        qs = cast(Self, super().values_list(*args, **kwargs))
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
        qs = super()._clone(**kwargs)  # type:ignore[misc]  # not in django stubs
        qs._do_iterate_profiles = self._do_iterate_profiles
        return qs

    def _get_related_profile_tables(self) -> List[str]:
        """
        See GenericUserProfile.related_profile_tables
        """
        if _is_profile(self.model):
            return []
        else:
            return self.model.related_profile_tables

    def select_related_profiles(self) -> Self:
        """
        Adds relevant select_related() joins so that user_to_profile() doesn't trigger extra queries
        """
        if _is_profile(self.model):
            # is already a profile table so no need to do any joins
            return self._clone()
        return self.select_related(*self.model.related_profile_tables)

    def prefetch_related_profiles(self) -> Self:
        """
        Adds relevant select_related() joins so that user_to_profile() doesn't trigger extra queries
        """
        if _is_profile(self.model):
            # is already a profile table so no need to do any joins
            return self._clone()
        return self.prefetch_related(*self.model.related_profile_tables)

    def iterator(self, chunk_size: Optional[int]=None):
        # extra validation check in case some subclass overwrote our other validation checks
        self._validate_iterator()
        return super().iterator(chunk_size)


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
        msg = f'A model with a GenericUserProfileManagerMixin ({model.__name__}.{manager_name}) ' \
              'is missing a related_profile_tables definition'
        raise NotImplementedError(msg)


_ManagerQuerySet = TypeVar("_ManagerQuerySet", covariant=True)


class GenericUserProfileManagerMixin(BaseUserManager):
    """
    Manager mixin that provides for iteration over user profiles.
    Is assumed to be a manager for a GenericUserProfile
    """

    # if you change this you may also want to narrow the types of some methods;
    # I can't find a way to explain to mypy that this can be overridden
    _queryset_class: type[GenericUserProfileQuerySet] = GenericUserProfileQuerySet
    _auto_select_related_profiles: bool
    _auto_prefetch_related_profiles: bool

    model: type[GenericUserProfile] # type:ignore[assignment] # narrow from parent definition

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

    def get_queryset(self) -> GenericUserProfileQuerySet:
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

    def contribute_to_class(self, model: type[Model], name):
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
        if not hasattr(model, 'related_profile_tables'):
            errors.append(checks.Error(
                f"Model '{model._meta.label}' does not define related_profile_tables",
                hint=f"Manager '{self.name}' needs related_profile_tables",
                obj=self.model,
                id=ID_ERROR_PROFILE_RELATED_TABLES,
            ))

        return errors

    def profiles(self) -> GenericUserProfileQuerySet:
        return self.get_queryset().profiles()

    # TODO: It would be nice to be able to do something like:
    #   SomeModel.objects.select_related('user__profile')
    # and have the '__profile' transformed into the relevant select_related() based on model.related_profile_tables
    # unfortunately the code to do the joins is baked into SQLCompiler.get_related_selections() and is not really
    # extensible without being very invasive
    #
    # Instead we have to call select_related_profiles on an unrelated queryset with a prefix

    def select_related_profiles(
        self,
        queryset: Optional[Union[GenericUserProfileQuerySet, GenericUserProfileManagerMixin]] = None,
        prefix: str = ""
    ) -> GenericUserProfileQuerySet:
        if bool(queryset) != bool(prefix):
            raise ValueError('Either none or both of queryset and prefix must be specified')

        if queryset is None:
            return self.get_queryset().select_related_profiles()
        else:
            filters = [prefix + '__' + profile for profile in self.model.related_profile_tables]
            return cast(GenericUserProfileQuerySet, queryset.select_related(*filters))

    def prefetch_related_profiles(
        self,
        queryset: Optional[Union[GenericUserProfileQuerySet, GenericUserProfileManagerMixin]] = None,
        prefix: str = ""
    ) -> GenericUserProfileQuerySet:
        if bool(queryset) != bool(prefix):
            raise ValueError('Either none or both of queryset and prefix must be specified')

        if queryset is None:
            return self.get_queryset().prefetch_related_profiles()
        else:
            filters = [prefix + '__' + profile for profile in self.model.related_profile_tables]
            return cast(GenericUserProfileQuerySet, queryset.prefetch_related(*filters))


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

    # This should be overridden to include a list of the FKs to the tables
    # to join to in order to fetch profiles [will be passed to select_related()]
    related_profile_tables: List[str]

    class Meta:
        abstract = True

    def get_profile(self) -> Self:
        # We're already a profile
        if _is_profile(type(self)):
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
        def __get__(
            self,
            obj: Optional[GenericUserProfile],
            cls: Optional[type[GenericUserProfile]] = None
        ) -> Union[Self, GenericUserProfile]:
            if obj is None:
                # class invocation
                return self

            user_profile = obj.get_profile()

            # cache the result on all records in the multi-table inheritance chain
            record: Optional[GenericUserProfile] = user_profile
            while isinstance(record, Model):
                record.__dict__['profile'] = user_profile

                # note that record.pk will always return the underlying pk id, not the user_ptr record
                # so we have to access it via the pk field's name and not the 'pk' alias
                pk = record._meta.pk
                record = getattr(record, pk.name)

            return user_profile

    # This isn't strictly the correct type; because this is a descriptor if you access this as a class property
    # (ie ClassName.profile) then you'll get the descriptor itself rather than the profile.
    # The overwhelming majority of the time you'll be accessing this via an instance (my_obj.profile) and want the
    # GenericUserProfile instance, so we type it for convenience rather than 100% accuracy
    profile: Self = cast(Self, _CachedProfileDescriptor())
