import django.contrib.auth.models as auth_models
from django.db import models

import allianceutils.auth.models


# We deliberately use a model with a non-standard USERNAME_FIELD to make sure
# that nothing is hardcoded to expect 'username' as the username field
class UserManager(allianceutils.auth.models.GenericUserProfileManagerMixin, auth_models.UserManager):
    def get_by_natural_key(self, username):
        return self.get(email=username)

    def get_by_natural_key(self, username: str) -> models.Model:
        username = self.normalize_email(username)
        return super().get_by_natural_key(username)
        return self.get(**{self.model.USERNAME_FIELD: username})

    def create_superuser(self, **kwargs):
        user = self.create_user(is_staff=True, is_superuser=True, **kwargs)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, is_staff=False, **kwargs):
        email = self.normalize_email(email)
        user = self.model(email=email, is_staff=is_staff, **kwargs)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(allianceutils.auth.models.GenericUserProfile, auth_models.AbstractBaseUser, auth_models.PermissionsMixin):
    USERNAME_FIELD = 'email'

    objects = UserManager()
    profiles = UserManager(select_related_profiles=True)
    related_profile_tables = [
        'customerprofile',
        'adminprofile',
    ]

    first_name = models.CharField(max_length=128, blank=True)
    last_name = models.CharField(max_length=128, blank=True)
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)

    def natural_key(self):
        return (self.email,)


class CustomerProfile(User):
    customer_details = models.CharField(max_length=191)


class AdminProfile(User):
    admin_details = models.CharField(max_length=191)


class UserFKImmediateModel(models.Model):
    fk = models.ForeignKey(to=User, on_delete=models.CASCADE)


class UserFKIndirectModel(models.Model):
    fk = models.ForeignKey(to=UserFKImmediateModel, on_delete=models.CASCADE)
