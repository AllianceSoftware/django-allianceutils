from typing import Optional
from unittest.mock import patch
import warnings

from django.conf import settings
from django.test import Client
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

# Compensation for the fact that django or other middleware may do some internal queries
QUERY_COUNT_OVERHEAD = 0


class QueryCountMiddlewareTestCase(TestCase):

    def assert_warning_count(self, expected_warnings: int, expected_log_warnings: int, count: int, set_threshold: Optional[int]=None):
        """
        :param expected_warnings: number of expected python warnings module warnings
        :param expected_log_warnings: number of expected python logging module warnings
        :param count: number of queryies to run
        :param set_threshold: override request.QUERY_COUNT_WARNING_THRESHOLD to this value
        """
        client = Client()

        data = {'count': str(int(count))}
        if set_threshold is not None:
            data['set_threshold'] = str(set_threshold)

        with warnings.catch_warnings(record=True) as w:
            with patch('allianceutils.middleware.query_count.logger.warning', autospec=True) as mock_warning:
                warnings.simplefilter('always')
                client.post(path=reverse('middleware:run_queries'), data=data)
                self.assertEqual(len(w), expected_warnings)
                self.assertEqual(expected_log_warnings, mock_warning.call_count)

    def test_do_nothing(self):
        """
        Ensure no false positives
        """
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD * 2)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.QueryCountMiddleware',))
    def test_not_exceeded(self):
        """
        Queries less than threshold
        """
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD - 1)
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD - 1)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.QueryCountMiddleware',))
    def test_exceeded(self):
        """
        Queries less than threshold
        """
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD - 1)
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD)
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD)
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD - 1)

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
        self.assert_warning_count(1, 0, 0)
        self.assert_warning_count(1, 1, settings.QUERY_COUNT_WARNING_THRESHOLD * 2)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.QueryCountMiddleware',))
    def test_increase_query_count(self):
        """
        Can temporarily increasing the query count threshold
        """
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD + 9, settings.QUERY_COUNT_WARNING_THRESHOLD + 10)
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD + 10, settings.QUERY_COUNT_WARNING_THRESHOLD + 10)
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD + 9, settings.QUERY_COUNT_WARNING_THRESHOLD + 10)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.QueryCountMiddleware',))
    def test_disable_query_count(self):
        """
        Query count threshold can be temporarily disabled
        """
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD * 2, '')
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD * 2)
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD * 2, '')
