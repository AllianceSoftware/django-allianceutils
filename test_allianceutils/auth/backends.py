
from allianceutils.auth.backends import MinimalModelBackend
from allianceutils.auth.backends import ProfileModelBackendMixin


# https://github.com/fusionbox/django-authtools/blob/6ea614ed2bba56cd8fa7209896b0e20cba45b367/authtools/backends.py#L5
# Copied out of authtools for use with django 3.2 tests where authtools no longer works
# This is probably not the best way to achieve this; now that django supports more advanced
# database indexing, it's better to use a case insensitive unique index on the User model
# as that can't be accidentally bypassed by badly behaved python code
class CaseInsensitiveUsernameFieldBackendMixin(object):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is not None:
            username = username.lower()

        return super(CaseInsensitiveUsernameFieldBackendMixin, self).authenticate(
            request,
            username=username,
            password=password,
            **kwargs
        )


class ProfileModelBackend(
    ProfileModelBackendMixin, CaseInsensitiveUsernameFieldBackendMixin, MinimalModelBackend
):
    pass
