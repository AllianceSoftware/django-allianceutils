from django.apps import apps
from django.core.checks import Error
from django.test import SimpleTestCase

from allianceutils.checks import check_explicit_table_names
from allianceutils.checks import ID_ERROR_EXPLICIT_TABLE_NAME
from allianceutils.checks import ID_ERROR_EXPLICIT_TABLE_NAME_LOWERCASE
from allianceutils.checks import make_check_explicit_table_names

from .checks_explicit_table_names.models import WithoutTableName
from .checks_explicit_table_names.models import WithTableNameUpperCase


class TestCheckExplicitTableNames(SimpleTestCase):

    def setUp(self):
        self.app_configs = [apps.get_app_config('checks_explicit_table_names')]

    def test_error_when_explicit_names_required(self):
        errors = check_explicit_table_names(self.app_configs)
        self.assertEqual(len(errors), 2)
        expected_errors = [
            Error(
                'Explicit table name required',
                hint='Add db_table setting to checks_explicit_table_names.WithoutTableName model Meta',
                obj=WithoutTableName,
                id=ID_ERROR_EXPLICIT_TABLE_NAME,
            ),
            Error(
                'Table names must be lowercase',
                hint='Check db_table setting for checks_explicit_table_names.WithTableNameUpperCase',
                obj=WithTableNameUpperCase,
                id=ID_ERROR_EXPLICIT_TABLE_NAME_LOWERCASE,
            )
        ]
        for error in expected_errors:
            self.assertIn(error, errors)

    def test_no_error_when_app_is_ignored(self):
        check = make_check_explicit_table_names(['checks_explicit_table_names'])
        errors = check(self.app_configs)
        self.assertEqual(len(errors), 0)

    def test_no_error_when_model_is_ignored(self):
        check = make_check_explicit_table_names(['checks_explicit_table_names.WithTableNameUpperCase'])
        errors = check(self.app_configs)
        self.assertEqual(len(errors), 1)
