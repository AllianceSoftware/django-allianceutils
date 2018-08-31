import threading
from typing import Dict
from typing import List
from typing import Optional
from unittest.mock import patch
import warnings

from django.conf import settings
from django.test import Client
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

# Compensation for the fact that django or other middleware may do some internal queries
from test_allianceutils.tests.middleware.views import reset_thread_wait_barrier

QUERY_COUNT_OVERHEAD = 0


class QueryCountMiddlewareTestCase(TestCase):

    def setUp(self):
        # If we don't use the same client for each request then the middleware is recreated each time
        # (ie it's as if every request is running in a new preocess)
        self.client = Client()

    def execute_request(self,
        url_path: str,
        data: Dict[str, str] = {},
        thread_count: int = 1,
    ):
        """
        Execute a request, optionally on multiple threads

        :param url_path: URL path to request
        :param data: POST variables
        :param thread_count: number of threads to create & run this request in

        :return: a list of responses if `thread_pool` more than 1, otherwise a single response
        """
        thread_exceptions = []
        thread_responses = []

        def do_request():
            try:
                response = self.client.post(path=url_path, data=data)
                thread_responses.append(response)
            except Exception as ex:
                thread_exceptions.append(ex)
                raise

        if thread_count == 1:
            do_request()
            return thread_responses[0]

        threads = [threading.Thread(target=do_request) for _ in range(thread_count)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if thread_exceptions:
            raise Exception(f'Found {len(thread_exceptions)} exception(s): {thread_exceptions}')

        return thread_responses

    def assert_warning_count(self,
        expected_warnings: int,
        expected_log_warnings: int,
        count: int,
        set_threshold: Optional[int]=None,
        thread_count: int = 1,
    ):
        """
        Make a request that executes `count` queries, and validate that the expected number of
        warnings is generated

        :param expected_warnings: number of expected python warnings module warnings
        :param expected_log_warnings: number of expected python logging module warnings
        :param count: number of queryies to run
        :param set_threshold: override request.QUERY_COUNT_WARNING_THRESHOLD to this value
        :param thread_count: number of threads to create & run this request in
        """
        data = {'count': str(int(count))}
        if set_threshold is not None:
            data['set_threshold'] = str(set_threshold)

        reset_thread_wait_barrier(thread_count if thread_count > 1 else 0)
        try:
            with warnings.catch_warnings(record=True) as w:
                with patch('allianceutils.middleware.query_count.logger.warning', autospec=True) as mock_logger_warning:
                    warnings.simplefilter('always')
                    self.execute_request(
                        url_path=reverse('middleware:run_queries'),
                        data=data,
                        thread_count=thread_count,
                    )
            self.assertEqual(len(w), expected_warnings)
            self.assertEqual(expected_log_warnings, mock_logger_warning.call_count)
        finally:
            reset_thread_wait_barrier(0)

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
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD + 9, set_threshold=settings.QUERY_COUNT_WARNING_THRESHOLD + 10)
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD + 10,set_threshold=settings.QUERY_COUNT_WARNING_THRESHOLD + 10)
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD + 9, set_threshold=settings.QUERY_COUNT_WARNING_THRESHOLD + 10)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.QueryCountMiddleware',))
    def test_disable_query_count(self):
        """
        Query count threshold can be temporarily disabled
        """
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD * 2, set_threshold='')
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD * 2)
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD * 2, set_threshold='')

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.QueryCountMiddleware',))
    def test_query_count_threaded(self):
        """
        test that QueryCountMiddleware works correctly with a multithreaded wsgi server
        """

        # because the queries are running in a different thread, there's an extra query as part of creating a new DB connection
        # for extra fun, it only happens on the *second* request

        thread_count = 4

        # django runs some extra queries for each new thread
        # the exact number depends on the django version
        url_path = reverse('middleware:query_overhead')
        responses = self.execute_request(url_path=url_path, thread_count=thread_count)
        request_overheads = [r.json()['data'] for r in responses]
        self.assertEqual(len(set(request_overheads)), 1)
        request_overhead = request_overheads[0]

        query_count_threshold = settings.QUERY_COUNT_WARNING_THRESHOLD - request_overhead - QUERY_COUNT_OVERHEAD - 1
        self.assert_warning_count(0, 0,            0,                         thread_count=thread_count)
        self.assert_warning_count(0, 0,            query_count_threshold,     thread_count=thread_count)
        self.assert_warning_count(0, thread_count, query_count_threshold + 1, thread_count=thread_count)
        self.assert_warning_count(0, 0,            query_count_threshold,     thread_count=thread_count)
        self.assert_warning_count(0, thread_count, query_count_threshold + 1, thread_count=thread_count)
