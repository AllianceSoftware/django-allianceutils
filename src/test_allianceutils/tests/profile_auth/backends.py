from __future__ import annotations

from typing import TYPE_CHECKING

from allianceutils.auth.backends import MinimalModelBackend
from allianceutils.auth.backends import ProfileModelBackendMixin
from test_allianceutils.tests.profile_auth.models import User


class ProfileModelBackend(ProfileModelBackendMixin, MinimalModelBackend):

    if TYPE_CHECKING:
        def get_user(self, user_id: int) -> User | None:  # type:ignore[override] # narrowing from superclass
            ...
