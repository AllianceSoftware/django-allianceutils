from typing import Optional

from authtools.backends import CaseInsensitiveUsernameFieldBackendMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Model

def resolve_rule_name(module, entity, action, is_global) -> str:
    """
    Used by csv_permissions to calculate rule names for each row
    """
    return f"{module}.{entity}_{action}"


UserModel = get_user_model()


class ProfileModelBackendMixin:
    """
    Will use User.profiles & get_profile() if present otherwise will fall back to default get_user() behaviour
    """

    def get_user(self, user_id):
        try:
            manager = UserModel.profiles
        except AttributeError:
            return super().get_user(user_id)

        try:
            user = manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

        return user if self.user_can_authenticate(user) else None


class MinimalModelBackend:
    """
    We've using this backend rather than just extending ModelBackend because the built-in django
    one requires the default django groups, permissions and user_permissions tables but we're
    using CSVPermissions instead
    """

    authenticate = ModelBackend.authenticate
    get_user = ModelBackend.get_user
    user_can_authenticate = ModelBackend.user_can_authenticate

    def has_perm(self, user: Model, perm: str, obj: Optional[Model] = None) -> bool:
        """
        We defer to other backends for the real logic
        """
        if user.is_superuser:
            return True
        return False


class ProfileModelBackend(
    ProfileModelBackendMixin, CaseInsensitiveUsernameFieldBackendMixin, MinimalModelBackend
):
    pass
