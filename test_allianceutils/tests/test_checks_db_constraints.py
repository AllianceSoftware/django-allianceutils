from django.core.checks import Error
from django.test import SimpleTestCase

from allianceutils.checks import check_db_constraints
from allianceutils.checks import ID_ERROR_DB_CONSTRAINTS


class TestCheckDBConstraints(SimpleTestCase):

    def test_warning(self):
        errors = check_db_constraints(None)
        # Each model will generate two errors
        app_name = 'checks_db_constraints'
        models = f'{app_name}.CheckDBConstraintA, {app_name}.CheckDBConstraintB'

        def err(app_model: str, constraint: str, truncated: str) -> Error:
            return Error(
                f'{app_model} constraint {constraint} is not unique',
                hint=f'Constraint truncates to {truncated}',
                obj=models,
                id=ID_ERROR_DB_CONSTRAINTS,
            )

        expect_errors = [
            err(
                'checks_db_constraints.CheckDBConstraintA',
                'native_bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__eeeeeeeeee',
                'native_bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__ddddd',
            ),
            err(
                'checks_db_constraints.CheckDBConstraintB',
                'native_bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__xxxxxxxxxx',
                'native_bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__ddddd',
            ),
            err(
                'checks_db_constraints.CheckDBConstraintA',
                'native_😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___aaaa',
                'native_😀😀😀😀😀😀😀😀😀😀😀😀😀😀',
            ),
            err(
                'checks_db_constraints.CheckDBConstraintB',
                'native_😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___bbbb',
                'native_😀😀😀😀😀😀😀😀😀😀😀😀😀😀',
            ),
        ]
        try:
            import django_db_constraints
        except ImportError:
            pass
        else:
            expect_errors += [
                err(
                    'checks_db_constraints.CheckDBConstraintA',
                    'shared_😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___aaaa',
                    'shared_😀😀😀😀😀😀😀😀😀😀😀😀😀😀',
                ),
                err(
                    'checks_db_constraints.CheckDBConstraintB',
                    'shared_😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___bbbb',
                    'shared_😀😀😀😀😀😀😀😀😀😀😀😀😀😀',
                ),
                err(
                    'checks_db_constraints.CheckDBConstraintA',
                    'bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__eeeeeeeeee',
                    'bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__',
                ),
                err(
                    'checks_db_constraints.CheckDBConstraintB',
                    'bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__xxxxxxxxxx',
                    'bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__',
                ),
                err(
                    'checks_db_constraints.CheckDBConstraintA',
                    '😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___aaaa',
                    '😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___',
                ),
                err(
                    'checks_db_constraints.CheckDBConstraintB',
                    '😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___bbbb',
                    '😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___',
                ),
            ]
        self.assertCountEqual(expect_errors, errors)
        # self.assertEqual(len(expect_errors), len(errors))
        # for i, expected_error in enumerate(expect_errors):
        #     self.assertIn(expected_error, errors)
