from django.apps import apps
from django.core.checks import Warning
from django.test import SimpleTestCase

from allianceutils.checks import check_autodumpdata
from allianceutils.checks import warning_autodumpdata_missing
from allianceutils.checks import warning_autodumpdata_proxy
import test_allianceutils.tests.autodumpdata.models as test_models


class TestCheckAutodumpdata(SimpleTestCase):

    def setUp(self):
        self.errors = check_autodumpdata(None)

    def assertNoModelErrors(self, model):
        # confirm that there are no warnings of any type relating to a given model
        self.assertEqual(0, len([err for err in self.errors if err.obj is model]))

    def test_warning(self):
        # nothing is set up to handle auth.Group
        warning = warning_autodumpdata_missing(apps.get_model('auth', 'Group'))
        self.assertIn(warning, self.errors)

    def test_ignore(self):
        # allianceutils.apps should exclude this
        model = apps.get_model('sessions', 'Session')
        self.assertNoModelErrors(model)

    def test_proxy_no_autodump(self):
        # proxy models should not raise a warning
        model = test_models.PublicationProxy
        self.assertNoModelErrors(model)

    def test_proxy_autodump(self):
        # proxy models with explicit fixture_autodump should raise a warning
        warning = warning_autodumpdata_proxy(test_models.BookProxy)
        self.assertIn(warning, self.errors)

    def test_abstract(self):
        # abstract models with or without autodumpdata should not raise a warning
        model = test_models.AbstractModel
        self.assertNoModelErrors(model)

        model = test_models.AbstractDumpModel
        self.assertNoModelErrors(model)

    def test_manytomany(self):
        # implicit manytomany tables should not warn
        model = apps.get_model('autodumpdata', 'Author_edited')
        self.assertNoModelErrors(model)

    def test_manytomany_through(self):
        # manytomany with explicit through table should not warn
        # Author.books is a FK with through=AuthorBook
        self.assertNoModelErrors(test_models.Author)
        self.assertNoModelErrors(test_models.AuthorBook)
        self.assertNoModelErrors(test_models.Book)
