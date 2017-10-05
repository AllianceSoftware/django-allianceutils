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


The problem with all of these is that they capture the content of every query, not just the number of queries

Instead we dynamically override cursor() on each connection and wrap execute() and executemany() for every
 returned cursor

"""
import warnings

from django.conf import settings
from django.db import connections

DEFAULT_QUERY_COUNT_WARNING_THRESHOLD = 50


class QueryCountWarning(UserWarning, ResourceWarning):
    pass


class QueryInterceptor:
    def __init__(self, callback_execute, callback_executemany, connection: object, alias: str):
        self.callback_execute = callback_execute
        self.callback_executemany = callback_executemany
        self.connection = connection
        self.alias = alias
        self.patched = None

    def __enter__(self):
        # we patch on the connection object itself; make sure there's nothing attached to the object
        if self.connection.__class__.cursor != self.connection.cursor.__func__:
            warnings.warn("Connection %s has already been patched; QueryCountMiddleware doing nothing" % self.alias)
            self.patched = False
        else:
            original_cursor = self.connection.cursor

            def patched_cursor(conn):
                cursor = original_cursor()

                if cursor.__class__.executemany != cursor.executemany.__func__ or \
                        cursor.__class__.execute != cursor.execute.__func__:
                    warnings.warn(
                        "Connection %s cursor has already been patched; QueryCountMiddleware doing nothing" % self.alias)

                original_execute = cursor.execute
                original_executemany = cursor.executemany

                def patched_execute(conn, sql, params=None):
                    self.callback_execute(sql, params)
                    return original_execute(sql, params)

                def patched_executemany(conn, sql, param_list):
                    self.callback_executemany(sql, param_list)
                    return original_executemany(sql, param_list)

                cursor.execute = patched_execute.__get__(cursor)
                cursor.executemany = patched_executemany.__get__(cursor)

                return cursor

            self.patched = True
            self.connection.cursor = patched_cursor.__get__(self.connection)

    def __exit__(self, ex_type, ex_value, ex_trace):
        if self.patched:
            delattr(self.connection, 'cursor')


class AllConnectionsInterceptor:
    def __init__(self, callback_execute, callback_executemany):
        self.callback_execute = callback_execute
        self.callback_executemany = callback_executemany
        self.interceptors = []

    def __enter__(self):
        for alias in settings.DATABASES:
            self.interceptors.append(QueryInterceptor(
                self.callback_execute,
                self.callback_executemany,
                connections[alias], alias
            ))
            self.interceptors[-1].__enter__()

    def __exit__(self, ex_type, ex_value, ex_trace):
        for interceptor in reversed(self.interceptors):
            interceptor.__exit__(ex_type, ex_value, ex_trace)


class QueryCountMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        self.query_count = 0

    def increment(self, sql, params):
        self.query_count += 1

    def __call__(self, request):
        # set up DB patching
        request.QUERY_COUNT_WARNING_THRESHOLD = getattr(settings, 'QUERY_COUNT_WARNING_THRESHOLD', DEFAULT_QUERY_COUNT_WARNING_THRESHOLD)

        with AllConnectionsInterceptor(self.increment, self.increment):
            response = self.get_response(request)

        if self.query_count > request.QUERY_COUNT_WARNING_THRESHOLD:
            warnings.warn('Request ran %d queries' % self.query_count, QueryCountWarning)

        return response
