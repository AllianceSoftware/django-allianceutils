from __future__ import annotations

from types import ModuleType

import django
from django.apps import apps
from django.conf import settings
from django.test import override_settings
from django.test import SimpleTestCase

from allianceutils.checks import CheckUrlTrailingSlash

rest_framework: ModuleType | None
try:
    import rest_framework
except ImportError:
    rest_framework = None

check_urls_settings = {
    'ROOT_URLCONF': 'test_allianceutils.tests.checks_slash_urls.urls',
    'MEDIA_URL': '/media/',
    'DEBUG': True, # need DEBUG otherwise static media URLs aren't included
    'INSTALLED_APPS': settings.INSTALLED_APPS + (
        'django.contrib.admin',
        'test_allianceutils.tests.checks_slash_urls',
    ),
}


class TestUrls(SimpleTestCase):

    @staticmethod
    def get_description(pattern):
        try:
            # django >= 2.0 simplified URLs
            return pattern.pattern.regex.pattern
        except AttributeError:
            # django <2.0 regex URLs
            return pattern.regex.pattern

    @staticmethod
    def get_errors(expect_trailing_slash):
        # Get a list of URLs with slash check errors
        app_configs = apps.get_app_configs()
        check = CheckUrlTrailingSlash(
            expect_trailing_slash=expect_trailing_slash,
            ignore_attrs={
                '_regex': [r'^ignoreme-regex'],
                '_route': ['ignoreme-simplified'],
            }
        )
        errors = check(app_configs)
        errors = [TestUrls.get_description(err.obj) for err in errors if err.id == 'allianceutils.W004']
        return errors

    def test_urls(self):
        """
        Base case: nothing should be wrong
        """
        errors = self.get_errors(expect_trailing_slash=True)
        self.assertEqual(errors, [])

    def assertUrlErrors(self, errors, expected):
        # In django 2.0+, regex url patterns containing '/' are *sometimes* .describe()d as r'\/'
        # we just strip out any r'\/' sequences to resolve this madness
        errors = [x.replace(r'\/', r'/') for x in errors]
        self.assertEqual(
            sorted(errors),
            sorted(expected)
        )

    @override_settings(**check_urls_settings)
    def test_missing_slash(self):
        """
        Test for URLs with a missing trailing slash
        """
        errors = self.get_errors(expect_trailing_slash=True)
        expected = [
            r'^noslash1\Z',
            r'^noslash2\Z',
            r'^noslash3\Z',
        ]
        if rest_framework:
            expected += [
                r'^api/noslash$',
                r'^api/noslash/(?P<pk>[^/.]+)$',
            ]
        self.assertUrlErrors(errors, expected)

    @override_settings(**check_urls_settings)
    def test_extra_slash(self):
        """
        Test for URLs with an extra trailing slash
        """
        errors = self.get_errors(expect_trailing_slash=False)
        expected = [
            r'^slash1/\Z',
            r'^slash2/\Z',
        ]
        if rest_framework:
            expected += [
                r'^api/slash/$',
                r'^api/slash/(?P<pk>[^/.]+)/$',
            ]
        self.assertUrlErrors(errors, expected)
