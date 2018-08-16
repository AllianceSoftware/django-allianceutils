from django.core.checks import Warning
from django.test import SimpleTestCase

from allianceutils.checks import check_db_constraints
from allianceutils.checks import ID_WARNING_DB_CONSTRAINTS


class TestCheckDBConstraints(SimpleTestCase):

    def test_warning(self):
        warnings = check_db_constraints(None)
        self.assertEqual(len(warnings), 2)
        app_name = 'checks_db_constraints'
        models = '{0}.CheckDBConstraintA, {0}.CheckDBConstraintB'.format(app_name)
        expect_warning = Warning(
            'These models have a duplicate DB constraint when truncated: '
            'bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__',
            hint='Ensure Meta.db_constraints for models %s are unique when truncated to 63 characters' % models,
            obj=models,
            id=ID_WARNING_DB_CONSTRAINTS,
        )
        self.assertEqual(warnings[0], expect_warning)

        expect_warning = Warning(
            'These models have a duplicate DB constraint when truncated: 😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___',
            hint='Ensure Meta.db_constraints for models %s are unique when truncated to 63 characters' % models,
            obj=models,
            id=ID_WARNING_DB_CONSTRAINTS,
        )
        self.assertEqual(warnings[1], expect_warning)
