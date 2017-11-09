import django.contrib.auth.models
from django.db import models

import allianceutils.models


class UserManager(django.contrib.auth.models.UserManager):
    def get_by_natural_key(self, username):
        return self.get(username=username)


class User(django.contrib.auth.models.AbstractUser):
    objects = UserManager()

    def natural_key(self):
        return (self.username,)


class CustomerProfile(User):
    customer_details = models.CharField(max_length=191)

    class Meta:
        manager_inheritance_from_future = True


class AdminProfile(User):
    admin_details = models.CharField(max_length=191)

    class Meta:
        manager_inheritance_from_future = True


class GenericUserProfileManager(allianceutils.models.GenericUserProfileManager, User._default_manager.__class__):
    use_proxy_model = False

    @classmethod
    def user_to_profile(cls, user):
        if hasattr(user, 'customerprofile'):
            return user.customerprofile
        elif hasattr(user, 'adminprofile'):
            return user.adminprofile
        return user

    @classmethod
    def select_related_profiles(cls, queryset):
        return queryset.select_related(
            'customerprofile',
            'adminprofile',
        )


class NoProxyUserProfileManager(GenericUserProfileManager):
    @classmethod
    def user_to_profile(cls, user):
        user = super().user_to_profile(user)
        if isinstance(user, (CustomerProfile, AdminProfile)):
            return user
        # this is a bit experimental
        user.__class__ = User
        return user


class GenericUserProfile(User):
    objects_noproxy = NoProxyUserProfileManager()
    objects_proxy = GenericUserProfileManager()


    # DoesNotExist = User.DoesNotExist
    # MultipleObjectsReturned = User.MultipleObjectsReturned

    class Meta:
        proxy = True
