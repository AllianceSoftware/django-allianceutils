import unittest

import django

if django.VERSION < (3, 2):
  default_app_config = 'allianceutils.apps.AllianceUtilsAppConfig'

# All the tests are in test_allianceutils
# Django's test autodiscovery will try to recursively import everything which causes asynctask to fail if we're running
# mysql tests
def load_tests(*args, **kwargs):
  empty_suite = unittest.TestSuite()
  return empty_suite

__version__ = "2.2.0"
