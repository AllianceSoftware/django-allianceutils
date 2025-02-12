from typing import _ProtocolMeta
from typing import TYPE_CHECKING
import unittest

from django.db.models.base import ModelBase

__version__ = "4.1.1"


# All the tests are in test_allianceutils
# Django's test autodiscovery will try to recursively import everything which causes asynctask to fail if we're running
# mysql tests
def load_tests(*args, **kwargs):
    empty_suite = unittest.TestSuite()
    return empty_suite


if TYPE_CHECKING:
    # This is intended for internal use; it's a workaround for the fact that
    # you can't inherit from both Model and Protocol
    # see https://stackoverflow.com/a/68925085
    #
    # It's not intended to be used at runtime, and is for type checking only

    class _ModelProtocolMeta(ModelBase, _ProtocolMeta):
        pass

    class ModelProtocol(metaclass=_ModelProtocolMeta):
        pass

else:
    class ModelProtocol:
        def __new__(cls):
            raise RuntimeError("ModelProtocol is for typing only and should not be used at runtime")