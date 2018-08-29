from django.core.checks import Error
from django.test import SimpleTestCase

from allianceutils.checks import check_db_constraints
from allianceutils.checks import ID_ERROR_DB_CONSTRAINTS


class TestCheckDBConstraints(SimpleTestCase):

    def test_warning(self):
        errors = check_db_constraints(None)
        # Each model will generate two errors
        self.assertEqual(len(errors), 4)
        app_name = 'checks_db_constraints'
        models = '{0}.CheckDBConstraintA, {0}.CheckDBConstraintB'.format(app_name)
        expect_errors = [
            Error(
                'checks_db_constraints.CheckDBConstraintA constraint bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__eeeeeeeeee is not unique',
                hint='Constraint truncates to bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__',
                obj=models,
                id=ID_ERROR_DB_CONSTRAINTS,
            ),
            Error(
                'checks_db_constraints.CheckDBConstraintA constraint 😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___aaaa is not unique',
                hint='Constraint truncates to 😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___',
                obj=models,
                id=ID_ERROR_DB_CONSTRAINTS,
            )
        ]
        for expected_error in expect_errors:
            self.assertIn(expected_error, errors)
