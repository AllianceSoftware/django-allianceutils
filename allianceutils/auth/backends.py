from typing import Optional

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
    Backend that provides authentication using User.profiles & get_profile().
    Will fall back to default get_user() behaviour if no profiles manager available
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
    Minimal backend for using built-in django User table for authentication but without using django's
    groups/permissions

    We don't extend ModelBackend because the built-in django one has various permissions-related functions we
    want to exclude entirely
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


try:
    from authtools.backends import CaseInsensitiveUsernameFieldBackendMixin
except ImportError:
    # no authtools present
    #
    # we could just remove CaseInsensitiveUsernameFieldBackendMixin from ProfileModelBackend but that
    # would mean devs who do an upgrade without reading the release notes would not notice that behaviour
    # had changed and would get unexpected silent failures. Is safer to remove this to force them to
    # deal with the issue
    pass
else:
    class ProfileModelBackend(
        ProfileModelBackendMixin, CaseInsensitiveUsernameFieldBackendMixin, MinimalModelBackend
    ):
        pass
