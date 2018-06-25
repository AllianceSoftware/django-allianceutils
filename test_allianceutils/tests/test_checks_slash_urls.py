from django.apps import apps
from django.conf import settings
from django.test import override_settings
from django.test import SimpleTestCase

from allianceutils.checks import check_url_trailing_slash

try:
    import rest_framework
except ImportError:
    rest_framework = None

check_urls_settings = {
    'ROOT_URLCONF': 'test_allianceutils.tests.checks_slash_urls.urls',
    'MEDIA_URL': '/media/',
    'DEBUG': True, # need DEBUG otherwise static media URLs aren't included
    'INSTALLED_APPS': settings.INSTALLED_APPS + ('test_allianceutils.tests.checks_slash_urls',),
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
        self.assertEqual(errors, [])

    @override_settings(**check_urls_settings)
    def test_missing_slash(self):
        """
        Test for URLs with a missing trailing slash
        """
        errors = self.get_errors(expect_trailing_slash=True)
        expected = [
            r'^noslash1$',
            r'^noslash2$',
            r'^noslash3$',
        ]
        if rest_framework:
            expected += [
                r'^api/noslash$',
                r'^api/noslash/(?P<pk>[^/.]+)$',
            ]
        self.assertEqual(sorted(errors), sorted(expected))

    @override_settings(**check_urls_settings)
    def test_extra_slash(self):
        """
        Test for URLs with an extra trailing slash
        """
        errors = self.get_errors(expect_trailing_slash=False)
        expected = [
            r'^slash1/$',
            r'^slash2/$',
        ]
        if rest_framework:
            expected += [
                r'^api/slash/$',
                r'^api/slash/(?P<pk>[^/.]+)/$',
            ]
        self.assertEqual(sorted(errors), sorted(expected))
