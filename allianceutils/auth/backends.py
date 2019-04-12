from django.contrib.auth import get_user_model
from authtools.backends import CaseInsensitiveEmailModelBackend

UserModel = get_user_model()


class ProfileModelBackend(CaseInsensitiveEmailModelBackend):
    """
    A variant of authtools.CaseInsensitiveEmailModelBackend which is a variant of
    django.contrib.auth.backends.ModelBackend that will use User.profiles &
    get_profile() if present otherwise will fall back to default django behaviour
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
