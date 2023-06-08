from __future__ import annotations

from typing import cast

from django.conf import settings
import django.contrib.auth.models as auth_models
from django.db import models

import allianceutils.auth.models


# We deliberately use a model with a non-standard USERNAME_FIELD to make sure
# that nothing is hardcoded to expect 'username' as the username field
class UserManager(allianceutils.auth.models.GenericUserProfileManagerMixin, auth_models.UserManager):
    def get_by_natural_key(self, username: str | None) -> User:  # type:ignore[override] # type narrowing from parent
        username = self.normalize_email(username)
        return cast(User, super().get_by_natural_key(username))

    def create_superuser(  # type:ignore[override] # email *is* username
        self,
        email: str,
        password: str | None = None,
        **kwargs
    ) -> User:
        if "username" in kwargs:
            raise RuntimeError("`username` has been hardcoded instead of using USERNAME_FIELD")
        if email is None:
            raise ValueError("Email cannot be empty")
        user = self.create_user(is_staff=True, is_superuser=True, email=email, password=password, **kwargs)
        user.save(using=self._db)
        return user

    def create_user(  # type:ignore[override] # email *is* username
        self,
        email: str,
        password: str | None = None,
        is_staff: bool = False,
        **kwargs
    ) -> User:
        if "username" in kwargs:
            raise RuntimeError("`username` is being used instead of USERNAME_FIELD")
        email = self.normalize_email(email)
        user = self.model(
            email=email,  # type:ignore[misc]  # email present on test User model
            is_staff=is_staff,
            **kwargs)
        user.set_password(password)  # type:ignore[attr-defined]  # set_password present on test User model
        user.save(using=self._db)
        assert isinstance(user, User)
        return user


ci_collations = {
    "django.db.backends.postgresql": "case_insensitive",  # we create this in a migration
    "django.db.backends.mysql": "utf8mb4_0900_ai_ci",  # default mysql CI collation
}

_db_engine = cast(str, settings.DATABASES["default"]["ENGINE"])  # type:ignore[misc]
_ci_collation = ci_collations[_db_engine]


class User(allianceutils.auth.models.GenericUserProfile, auth_models.AbstractBaseUser, auth_models.PermissionsMixin):
    USERNAME_FIELD = 'email'

    objects = UserManager()  # type:ignore[assignment] # overriding super
    profiles: UserManager = UserManager(select_related_profiles=True)  # type:ignore[assignment] # overriding super
    related_profile_tables = [
        'customerprofile',
        'adminprofile',
    ]

    first_name = models.CharField(max_length=128, blank=True)
    last_name = models.CharField(max_length=128, blank=True)
    email = models.EmailField(
        db_collation=_ci_collation,
        max_length=191,
        unique=True,
    )
    is_staff = models.BooleanField(default=False)

    def natural_key(self) -> tuple[str]:
        email: str = self.email
        return (email, )


class CustomerProfile(User):
    customer_details = models.CharField(max_length=191)


class AdminProfile(User):
    admin_details = models.CharField(max_length=191)


class UserFKImmediateModel(models.Model):
    fk = models.ForeignKey(to=User, on_delete=models.CASCADE)


class UserFKIndirectModel(models.Model):
    fk = models.ForeignKey(to=UserFKImmediateModel, on_delete=models.CASCADE)
