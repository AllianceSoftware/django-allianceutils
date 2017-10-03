from django.apps import apps
from django.conf import settings
from django.test import override_settings
from django.test import SimpleTestCase

from allianceutils.checks import check_url_trailing_slash


class TestUrls(SimpleTestCase):

    @staticmethod
    def get_errors():
        # Get a list of URLs with slash check errors
        app_configs = apps.get_app_configs()
        errors = check_url_trailing_slash(app_configs)
        errors = [err.obj.regex.pattern for err in errors if err.id == 'allianceutils.W004']
        return errors

    def test_urls(self):
        """
        Base case: nothing should be wrong
        """
        errors = self.get_errors()
        self.assertEquals(errors, [])

    @override_settings(
        APPEND_SLASH=True,
        ROOT_URLCONF='allianceutils.tests.checks_slash_urls.urls',
        INSTALLED_APPS=settings.INSTALLED_APPS + ('allianceutils.tests.checks_slash_urls',),
    )
    def test_missing_slash(self):
        """
        Test for URLs with a missing trailing slash
        """
        errors = self.get_errors()
        expected = [
            '^noslash1$',
            '^noslash2$',
            '^noslash3$',
        ]
        self.assertEquals(sorted(errors), sorted(expected))

    @override_settings(
        APPEND_SLASH=False,
        ROOT_URLCONF='allianceutils.tests.checks_slash_urls.urls',
        INSTALLED_APPS=settings.INSTALLED_APPS + ('allianceutils.tests.checks_slash_urls',),
    )
    def test_extra_slash(self):
        """
        Test for URLs with an extra trailing slash
        """
        errors = self.get_errors()
        expected = [
            '^slash1/$',
            '^slash2/$',
        ]
        self.assertEquals(sorted(errors), sorted(expected))
