from django.apps import apps
from django.conf import settings
from django.test import override_settings
from django.test import SimpleTestCase

from allianceutils.checks import check_url_trailing_slash

check_urls_settings = {
    'ROOT_URLCONF': 'allianceutils.tests.checks_slash_urls.urls',
    'MEDIA_URL': '/media/',
    'DEBUG': True, # need DEBUG otherwise static media URls aren't included
    'INSTALLED_APPS': settings.INSTALLED_APPS + ('allianceutils.tests.checks_slash_urls',),
}


class TestUrls(SimpleTestCase):

    @staticmethod
    def get_errors(expect_trailing_slash):
        # Get a list of URLs with slash check errors
        app_configs = apps.get_app_configs()
        check = check_url_trailing_slash(
            expect_trailing_slash=expect_trailing_slash,
            ignore_attrs={
                '_regex': [r'^ignoreme'],
            }
        )
        errors = check(app_configs)
        errors = [err.obj.regex.pattern for err in errors if err.id == 'allianceutils.W004']
        return errors

    def test_urls(self):
        """
        Base case: nothing should be wrong
        """
        errors = self.get_errors(expect_trailing_slash=True)
        self.assertEquals(errors, [])

    @override_settings(**check_urls_settings)
    def test_missing_slash(self):
        """
        Test for URLs with a missing trailing slash
        """
        errors = self.get_errors(expect_trailing_slash=True)
        expected = [
            '^noslash1$',
            '^noslash2$',
            '^noslash3$',
        ]
        self.assertEquals(sorted(errors), sorted(expected))

    @override_settings(**check_urls_settings)
    def test_extra_slash(self):
        """
        Test for URLs with an extra trailing slash
        """
        errors = self.get_errors(expect_trailing_slash=False)
        expected = [
            '^slash1/$',
            '^slash2/$',
        ]
        self.assertEquals(sorted(errors), sorted(expected))
