from django.core.checks import Error
from django.test import SimpleTestCase

from allianceutils.checks import check_admins
from allianceutils.checks import ID_ERROR_ADMINS

ADMINS_ERROR = Error(
    'settings.ADMINS should not be empty',
    obj='settings',
    id=ID_ERROR_ADMINS,
)


class TestCheckAdmins(SimpleTestCase):

    def test_warns_on_empty_admins_in_production(self):
        settings = {
            'AUTOMATED_TESTS': False,
            'DEBUG': False,
            'ADMINS': (),
        }
        with self.settings(**settings):
            errors = check_admins(None)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0], ADMINS_ERROR)

        settings = {
            'AUTOMATED_TESTS': False,
            'DEBUG': False,
            'ADMINS': (
                'admin@admin.com',
            ),
        }
        with self.settings(**settings):
            errors = check_admins(None)
            self.assertEqual(len(errors), 0)

    def test_does_not_warn_on_empty_admins_in_dev(self):
        settings = {
            'AUTOMATED_TESTS': True,
            'DEBUG': False,
            'ADMINS': (),
        }
        with self.settings(**settings):
            self.assertEqual(len(check_admins(None)), 0)

        settings = {
            'AUTOMATED_TESTS': False,
            'DEBUG': True,
            'ADMINS': (),
        }
        with self.settings(**settings):
            self.assertEqual(len(check_admins(None)), 0)

        settings = {
            'AUTOMATED_TESTS': True,
            'DEBUG': True,
            'ADMINS': (),
        }
        with self.settings(**settings):
            self.assertEqual(len(check_admins(None)), 0)
