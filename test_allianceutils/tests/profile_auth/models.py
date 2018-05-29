import django.contrib.auth.models
from django.db import models

import allianceutils.auth.models


class UserManager(allianceutils.auth.models.GenericUserProfileManagerMixin, django.contrib.auth.models.UserManager):
    def get_by_natural_key(self, username):
        return self.get(username=username)


class User(allianceutils.auth.models.GenericUserProfile, django.contrib.auth.models.AbstractUser):
    objects = UserManager()
    profiles = UserManager(select_related_profiles=True)
    related_profile_tables = [
        'customerprofile',
        'adminprofile',
    ]

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


class UserFKImmediateModel(models.Model):
    fk = models.ForeignKey(to=User, on_delete=models.CASCADE)


class UserFKIndirectModel(models.Model):
    fk = models.ForeignKey(to=UserFKImmediateModel, on_delete=models.CASCADE)
