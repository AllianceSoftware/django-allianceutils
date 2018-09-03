"""
Unfortunately django.db.connection doesn't record queries unless DEBUG=True
We want this to work in production too so we have to wrap the database connections with our own func

Possible strategies:

- check len(django.db.connection)
    - this only works if DEBUG is True
    - Execution flow is:
        - BaseDatabaseWrapper._prepare_cursor()
            - BaseDatabaseWrapper.make[_debug]_cursor()
                - CursorDebugWrapper.execute()
                - CursorDebugWrapper.executemany()

- Set BaseDatabaseWrapper.force_debug_cursor on each connection to True
    - see django.test.testcases.TransactionTestCase.assertNumQueries()
        - see django.test.utils.CaptureQueriesContext
    - see https://github.com/YPlan/django-perf-rec/blob/2.1.0/django_perf_rec/db.py

The problem with both of these is that they capture the content of every query, not just the number of queries
This data can get quite large depending on the application

- Set connection.cursor() to be a wrapper function and have this call to the underlying connection.__class__.cursor()
    - django debug toolbar takes this approach, but doesn't play well with other apps: it doesn't correctly restore an
      existing connection.cursor attribute
    - this still works for the cursor though, since unlike connections we never need to restore it to the original state

Instead we dynamically create a new class for the connection to override cursor() and have this call the parent


NOTE: We could have used django signals but since this is going to be called on every single SQL query we want to
avoid the associated overhead
"""
import logging
from typing import Callable
from typing import List
import warnings

from django.conf import settings
from django.db import connections
from django.http import HttpRequest
from django.http import HttpResponse

DEFAULT_QUERY_COUNT_WARNING_THRESHOLD = 50

logger = logging.getLogger('django.db')


def _patched_execute(cursor, sql, params=None):
    """
    Patch function that is used to replace execute() on a database connection
    """
    cursor.querycountmiddleware_callback_execute(sql, params)
    return cursor.querycountmiddleware_original_execute(sql, params)


def _patched_executemany(cursor, sql, param_list):
    """
    Patch function that is used to replace executemany() on a database connection
    """
    cursor.querycountmiddleware_callback_executemany(sql, param_list)
    return cursor.querycountmiddleware_original_executemany(sql, param_list)


class ConnectionCallbackMixin:
    def cursor(self, *args, **kwargs):
        cursor = super().cursor(*args, **kwargs)

        # make sure noone else has tried to patch execute()/executemany() on the object
        if cursor.__class__.executemany != cursor.executemany.__func__ or cursor.__class__.execute != cursor.execute.__func__:
            warnings.warn("Connection '{self.alias}' cursor has already been patched; ConnectionCallbackMixin doing nothing", RuntimeWarning)
            return cursor

        cursor.querycountmiddleware_callback_execute = self.querycountmiddleware_callback_execute
        cursor.querycountmiddleware_callback_executemany = self.querycountmiddleware_callback_executemany
        cursor.querycountmiddleware_original_execute = cursor.execute
        cursor.querycountmiddleware_original_executemany = cursor.executemany

        cursor.execute = _patched_execute.__get__(cursor)
        cursor.executemany = _patched_executemany.__get__(cursor)

        return cursor


class QueryObserver:
    callback_execute: Callable
    callback_executemany: Callable
    connection: object
    alias: str
    patch_applied: bool

    def __init__(self, callback_execute: Callable, callback_executemany: Callable, connection: object, alias: str):
        self.callback_execute = callback_execute
        self.callback_executemany = callback_executemany
        self.connection = connection
        self.alias = alias
        self.patch_applied = False

    def __enter__(self):
        if isinstance(self.connection, ConnectionCallbackMixin):
            # This could be a hard exception but we don't want to kill the server in production if someone screws up
            warnings.warn(f"Can't patch connection '{self.alias}' with QueryObserver multiple times", RuntimeWarning)
            return

        # TODO: At some point we might cache these generated classes so we don't have to recreate it every time
        original_class = self.connection.__class__
        PatchedConnectionClass = type(
            'QueryCountMiddleware' + original_class.__name__,
            (ConnectionCallbackMixin, original_class),
            {'querycountmiddleware_original_class': original_class},
        )

        self.connection.__class__ = PatchedConnectionClass
        self.patch_applied = True
        self.connection.querycountmiddleware_callback_execute =  self.callback_execute
        self.connection.querycountmiddleware_callback_executemany = self.callback_executemany

    def __exit__(self, ex_type, ex_value, ex_trace):
        if not self.patch_applied:
            return

        if not isinstance(self.connection, ConnectionCallbackMixin):
            msg = f"Connection '{self.alias}' has been unexpectedly changed; QueryCountMiddleware cannot cleanup"
            warnings.warn(msg, RuntimeWarning )
            return

        self.connection.__class__ = self.connection.querycountmiddleware_original_class
        delattr(self.connection, 'querycountmiddleware_callback_execute')
        delattr(self.connection, 'querycountmiddleware_callback_executemany')


class AllConnectionsQueryObserver:
    """
    Intercepts calls to every DB connection for
    - execute()
    - executemany()
    """

    callback_execute: Callable
    callback_executemany: Callable
    observers: List[QueryObserver]

    def __init__(self, callback_execute: Callable, callback_executemany: Callable):
        self.callback_execute = callback_execute
        self.callback_executemany = callback_executemany
        self.observers = []

    def __enter__(self):
        for alias in settings.DATABASES:
            observer = QueryObserver(
                self.callback_execute,
                self.callback_executemany,
                connections[alias],
                alias
            )
            self.observers.append(observer)
            observer.__enter__()

    def __exit__(self, ex_type, ex_value, ex_trace):
        for interceptor in reversed(self.observers):
            interceptor.__exit__(ex_type, ex_value, ex_trace)


class QueryCountMiddleware:
    get_response: Callable

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # check for QueryCountMiddleware being included twice
        if getattr(request, 'querycountmiddleware', None) not in (None, self):
            msg = "QueryCountMiddleware appears to be already initialised (did you include QueryCountMiddleware multiple times?)"
            warnings.warn(msg, RuntimeWarning)
            return self.get_response(request)

        request.querycountmiddleware = self
        request.querycountmiddleware_query_count = 0
        request.QUERY_COUNT_WARNING_THRESHOLD = getattr(settings, 'QUERY_COUNT_WARNING_THRESHOLD', DEFAULT_QUERY_COUNT_WARNING_THRESHOLD)

        def increment_query_count(*args, **kwargs):
            request.querycountmiddleware_query_count += 1

        with AllConnectionsQueryObserver(increment_query_count, increment_query_count):
            response = self.get_response(request)

        query_count = request.querycountmiddleware_query_count
        if getattr(request, 'QUERY_COUNT_WARNING_THRESHOLD', 0) and query_count >= request.QUERY_COUNT_WARNING_THRESHOLD:
            logger.warning(f'excessive query count: request "{request.method} {request.path}" ran {query_count} queries')

        return response
