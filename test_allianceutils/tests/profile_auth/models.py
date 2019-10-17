from authtools.models import AbstractEmailUser
from authtools.models import UserManager
from django.db import models

import allianceutils.auth.models


class UserManager(allianceutils.auth.models.GenericUserProfileManagerMixin, UserManager):
    def get_by_natural_key(self, username):
        return self.get(email=username)


class User(allianceutils.auth.models.GenericUserProfile, AbstractEmailUser):
    objects = UserManager()
    profiles = UserManager(select_related_profiles=True)
    related_profile_tables = [
        'customerprofile',
        'adminprofile',
    ]

    first_name = models.CharField(max_length=128, blank=True)
    last_name = models.CharField(max_length=128, blank=True)
    email = models.EmailField(unique=True)

    def natural_key(self):
        return (self.email,)


class CustomerProfile(User):
    customer_details = models.CharField(max_length=191)

    class Meta:
        manager_inheritance_from_future = True


class AdminProfile(User):
    admin_details = models.CharField(max_length=191)

    class Meta:
        manager_inheritance_from_future = True


class UserFKImmediateModel(models.Model):
    fk = models.ForeignKey(to=User, on_delete=models.CASCADE)


class UserFKIndirectModel(models.Model):
    fk = models.ForeignKey(to=UserFKImmediateModel, on_delete=models.CASCADE)
