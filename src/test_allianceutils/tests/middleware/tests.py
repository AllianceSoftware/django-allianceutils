from __future__ import annotations

import base64
import threading
from typing import Callable
from typing import Dict
from typing import Optional
from unittest.mock import patch
import warnings

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

# Compensation for the fact that django or other middleware may do some internal queries
from allianceutils.middleware import CurrentUserMiddleware
from test_allianceutils.tests.middleware.views import reset_thread_wait_barrier

QUERY_COUNT_OVERHEAD = 0


def execute_request(client: Client | None,
    url_path: str,
    data: Dict[str, str] = {},
    thread_count: int = 1,
    prehook: Callable[[Client | None, int | None], Client] | None = None,
):
    """
    Execute a request, optionally on multiple threads

    :param url_path: URL path to request
    :param data: POST variables
    :param thread_count: number of threads to create & run this request in
    :param prehook: if passed will call this with the Client to allow for login / other setup

    :return: a list of responses if `thread_pool` more than 1, otherwise a single response
    """
    thread_exceptions = []
    thread_responses = []

    def do_request(client: Client | None=None, count: int | None=None):
        try:
            if prehook:
                client = prehook(client, count)
            assert client is not None
            response = client.post(path=url_path, data=data)
            thread_responses.append(response)
        except Exception as ex:
            thread_exceptions.append(ex)
            raise

    if thread_count == 1:
        do_request(client, 0)
        return thread_responses[0]

    threads = [threading.Thread(target=do_request, args=(client, count)) for count in range(thread_count)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if thread_exceptions:
        raise Exception(f'Found {len(thread_exceptions)} exception(s): {thread_exceptions}')

    return thread_responses


class CurrentUserMiddlewareTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'user@ue.c'
        self.password = 'password'
        user = get_user_model().objects.create_user(email=self.username, password=self.password)
        self.user_id = user.id
        self.path = reverse('middleware:current_user')

    def tearDown(self):
        get_user_model().objects.all().delete()

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'allianceutils.middleware.CurrentUserMiddleware',
    ))
    def test_able_to_get_none_from_middleware_when_anonymous(self):
        user = self.client.post(path=self.path).json()['username']
        self.assertEqual(user, None)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'allianceutils.middleware.CurrentUserMiddleware',
    ))
    def test_able_to_get_current_user_from_middleware(self):
        self.client.login(username=self.username, password=self.password)
        user = self.client.post(path=self.path).json()['username']
        self.assertEqual(user, self.username)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'allianceutils.middleware.CurrentUserMiddleware',
    ))
    def test_able_to_get_current_user_from_middleware_from_respective_threads(self):
        def create_user_and_login(client, count):
            client = Client()
            count = str(count)
            get_user_model().objects.create_user(email=count, password=count)
            client.login(username=count, password=count)
            return client

        THREAD_COUNTS = 13
        responses = execute_request(
            client=None,
            url_path=self.path,
            thread_count=THREAD_COUNTS,
            prehook=create_user_and_login
        )

        usernames = set([response.json()['username'] for response in responses])
        expected_usernames = set([str(i) for i in range(THREAD_COUNTS)])
        self.assertEqual(usernames, expected_usernames)

    def test_not_active_for_thread(self):
        with self.assertRaisesRegex(KeyError, f"Thread .* not already registered with CurrentUserMiddleware"):
            CurrentUserMiddleware.get_user()


class QueryCountMiddlewareTestCase(TestCase):

    def setUp(self):
        # If we don't use the same client for each request then the middleware is recreated each time
        # (ie it's as if every request is running in a new preocess)
        self.client = Client()

    def assert_warning_count(self,
        expected_warnings: int,
        expected_log_warnings: int,
        count: int,
        set_threshold: Optional[int]=None,
        throw_exception: bool=False,
        thread_count: int = 1,
    ):
        """
        Make a request that executes `count` queries, and validate that the expected number of
        warnings is generated

        :param expected_warnings: number of expected python warnings module warnings
        :param expected_log_warnings: number of expected python logging module warnings
        :param count: number of queryies to run
        :param set_threshold: override request.QUERY_COUNT_WARNING_THRESHOLD to this value
        :param throw_exception: whether the request should throw an exception before returning
        :param thread_count: number of threads to create & run this request in
        """
        data = {
            'count': str(int(count)),
            'throw_exception': str(throw_exception),
        }
        if set_threshold is not None:
            data['set_threshold'] = str(set_threshold)

        reset_thread_wait_barrier(thread_count if thread_count > 1 else 0)
        try:
            with warnings.catch_warnings(record=True) as w:
                with patch('allianceutils.middleware.query_count.logger.warning', autospec=True) as mock_logger_warning:
                    warnings.simplefilter('always')
                    execute_request(
                        client=self.client,
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
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD // 2)

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
        Queries more than threshold
        """
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD - 1)
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD)
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD + settings.QUERY_COUNT_WARNING_THRESHOLD)
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
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD * 2, set_threshold=0)
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD * 2)
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD * 2, set_threshold=0)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.QueryCountMiddleware',))
    def test_exception(self):
        """
        QueryCountMiddleware works even if an exception is thrown
        """
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD - 1)
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD)
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD, throw_exception=True)
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD - 1, throw_exception=True)
        self.assert_warning_count(0, 0, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD - 1)
        self.assert_warning_count(0, 1, settings.QUERY_COUNT_WARNING_THRESHOLD - QUERY_COUNT_OVERHEAD)

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
        responses = execute_request(client=self.client, url_path=url_path, thread_count=thread_count)
        request_overheads = [r.json()['data'] for r in responses]
        self.assertEqual(len(set(request_overheads)), 1)
        request_overhead = request_overheads[0]

        query_count_threshold = settings.QUERY_COUNT_WARNING_THRESHOLD - request_overhead - QUERY_COUNT_OVERHEAD - 1
        self.assert_warning_count(0, 0,            0,                         thread_count=thread_count)
        self.assert_warning_count(0, 0,            query_count_threshold,     thread_count=thread_count)
        self.assert_warning_count(0, thread_count, query_count_threshold + 1, thread_count=thread_count)
        self.assert_warning_count(0, 0,            query_count_threshold,     thread_count=thread_count)
        self.assert_warning_count(0, thread_count, query_count_threshold + 1, thread_count=thread_count)


class HttpAuthMiddlewareTestCase(TestCase):
    username = 'TehLocalFooties'
    password = 'Toazted:Mushr0m'

    def setUp(self):
        self.client = Client()

    @override_settings(HTTP_AUTH_USERNAME=username, HTTP_AUTH_PASSWORD=password)
    def test_site_accessible_without_middleware(self):
        resp = self.client.get(path="/")
        self.assertEqual(resp.status_code, 404)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.HttpAuthMiddleware',))
    def test_site_accessible_with_middleware_but_no_config(self):
        resp = self.client.get(path="/")
        self.assertEqual(resp.status_code, 404)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.HttpAuthMiddleware',), HTTP_AUTH_USERNAME=username, HTTP_AUTH_PASSWORD=password)
    def test_site_inaccessible_without_any_auth(self):
        resp = self.client.get(path="/")
        self.assertEqual(resp.status_code, 401)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.HttpAuthMiddleware',), HTTP_AUTH_USERNAME=username, HTTP_AUTH_PASSWORD=password)
    def test_site_inaccessible_with_incorrect_auth(self):
        resp = self.client.get(
            path="/",
            HTTP_AUTHORIZATION="Basic " + str(base64.b64encode(b'a:b'), 'utf-8'),
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(MIDDLEWARE=settings.MIDDLEWARE + ('allianceutils.middleware.HttpAuthMiddleware',), HTTP_AUTH_USERNAME=username, HTTP_AUTH_PASSWORD=password)
    def test_site_accessible_with_correct_auth(self):
        resp = self.client.get(
            path="/",
            HTTP_AUTHORIZATION="Basic " + str(base64.b64encode(f'{self.username}:{self.password}'.encode()), 'utf-8')
        )
        self.assertEqual(resp.status_code, 404)
