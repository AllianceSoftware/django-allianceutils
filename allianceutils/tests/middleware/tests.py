#from unittest.mock import patch
import warnings

from django.conf import settings
from django.test import Client
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

#import allianceutils.middleware.query_count.warnings.warn
from allianceutils.middleware import QueryCountWarning

# Compensation for the fact that django or other middleware may do some internal queries
QUERY_COUNT_OVERHEAD = 0


class QueryCountMiddlewareTestCase(TestCase):

    def test_do_nothing(self):
        """
        Ensure no false positives
        """
        client = Client()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            client.post(
                path=reverse('middleware:run_queries'),
                data={'count': settings.QUERY_COUNT_WARNING_THRESHOLD * 2},
            )
            self.assertEquals(len(w), 0)

    @override_settings(
        MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.QueryCountMiddleware',),
    )
    def test_not_exceeded(self):
        """
        Queries less than threshold
        """
        client = Client()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always', QueryCountWarning)
            client.post(
                path=reverse('middleware:run_queries'),
                data={'count': str(settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD)},
            )
            self.assertEquals(len(w), 0)

    @override_settings(
        MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.QueryCountMiddleware',),
    )
    def test_exceeded(self):
        """
        Queries less than threshold
        """
        client = Client()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always', QueryCountWarning)
            client.post(
                path=reverse('middleware:run_queries'),
                data={'count': str(settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD + 1)},
            )
            self.assertEquals(len(w), 1)

    @override_settings(
        MIDDLEWARE=settings.MIDDLEWARE + (
            'allianceutils.middleware.QueryCountMiddleware',
            'allianceutils.middleware.QueryCountMiddleware',
        ),
    )
    def test_duplicate_middleware(self):
        """
        Middleware included more than once;
        - first copy should work as normal
        - second copy should give a warning that it is a duplicate
        """
        client = Client()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            client.post(
                path=reverse('middleware:run_queries'),
                data={'count': str(0)},
            )
            self.assertEquals(len(w), 1)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            client.post(
                path=reverse('middleware:run_queries'),
                data={'count': str(settings.QUERY_COUNT_WARNING_THRESHOLD*2)},
            )
            self.assertEquals(len(w), 2)
