# from authtools.models import AbstractEmailUser
from django.contrib.auth.models import AbstractUser
from django.db import models

import allianceutils.models


class User(AbstractUser):
# class User(AbstractEmailUser):
    pass


class CustomerProfile(User):
    customer_details = models.CharField(max_length=191)


class AdminProfile(User):
    admin_details = models.CharField(max_length=191)


class UserProfileManager(allianceutils.models.GenericUserProfileManager):
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


class ProxyUserProfileManager(UserProfileManager):
    use_proxy_model = True


class GenericUserProfile(User):
    objects = UserProfileManager()
    objects_proxy = ProxyUserProfileManager()

    class Meta:
        proxy = True
