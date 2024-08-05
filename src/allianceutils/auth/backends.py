from __future__ import annotations

from typing import Optional
from typing import Protocol

from allianceutils.auth.models import GenericUserProfile
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Model


def resolve_perm_name(module, entity, action, is_global) -> str:
    """
    Used by csv_permissions to calculate rule names for each row
    """
    return f"{module}.{entity}_{action}"


UserModel = get_user_model()


class _BaseUserModelBackend(Protocol):
    def get_user(self, user_id):
        ...

    def user_can_authenticate(self, user: Model):
        ...


class _BaseUserModel(Protocol):
    is_superuser: bool


class ProfileModelBackendMixin:
    """
    Backend that provides authentication using User.profiles & get_profile().
    Will fall back to default get_user() behaviour if no profiles manager available
    """

    def get_user(self: _BaseUserModelBackend, user_id) -> Optional[GenericUserProfile]:
        try:
            manager = UserModel.profiles
        except AttributeError:
            return super().get_user(user_id)  # type: ignore[safe-super]

        try:
            user = manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

        return user if self.user_can_authenticate(user) else None


class MinimalModelBackend:
    """
    Minimal backend for using built-in django User table for authentication but without using django's
    groups/permissions

    We don't extend ModelBackend because the built-in django one has various permissions-related functions we
    want to exclude entirely
    """

    authenticate = ModelBackend.authenticate
    get_user = ModelBackend.get_user
    user_can_authenticate = ModelBackend.user_can_authenticate

    def has_perm(self, user: _BaseUserModel, perm: str, obj: Optional[Model] = None) -> bool:
        """
        We defer to other backends for the real logic
        """
        if user.is_superuser:
            return True
        return False
