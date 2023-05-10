from django.apps import apps
from django.core.checks import Error
from django.test import SimpleTestCase

from allianceutils.checks import CheckReversibleFieldNames
from allianceutils.checks import ID_ERROR_FIELD_NAME_NOT_CAMEL_FRIENDLY

from .checks_field_names.models import NameWithUnderscoreNumberInMiddle
from .checks_field_names.models import NameWithUnderscoreRightBeforeNumber


class TestCheckFieldNames(SimpleTestCase):

    def setUp(self):
        self.app_configs = [apps.get_app_config('checks_field_names')]

    def test_for_underscores_preceding_numbers_gets_reported_correctly(self):
        errors = CheckReversibleFieldNames()(self.app_configs)
        self.assertEqual(len(errors), 2)

        expected_errors = [
            Error(
                'Field name is not reversible with underscore_to_camel()/camel_to_underscore()',
                hint='Underscore before a number in checks_field_names.NameWithUnderscoreRightBeforeNumber.name_1',
                obj=NameWithUnderscoreRightBeforeNumber,
                id=ID_ERROR_FIELD_NAME_NOT_CAMEL_FRIENDLY,
            ),
            Error(
                'Field name is not reversible with underscore_to_camel()/camel_to_underscore()',
                hint='Underscore before a number in checks_field_names.NameWithUnderscoreNumberInMiddle.name_complex_1_field',
                obj=NameWithUnderscoreNumberInMiddle,
                id=ID_ERROR_FIELD_NAME_NOT_CAMEL_FRIENDLY,
            ),
        ]

        for error in expected_errors:
            self.assertIn(error, errors)

        self.assertEqual(len(errors), len(expected_errors))
