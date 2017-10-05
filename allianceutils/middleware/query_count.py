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

- Set connection.cursor() to be a wrapper function and have this call to the underlying connection.__class__.cursor()
    - django debug toolbar takes this approach, but doesn't play well with other apps: it doesn't correctly restore an
      existing connection.cursor attribute
    - this still works for the cursor though, since unlike connections we never need to restore it to the original state

Instead we dynamically create a new class for the connection to override cursor() and have this call the parent

"""
import logging
import warnings

from django.conf import settings
from django.db import connections

DEFAULT_QUERY_COUNT_WARNING_THRESHOLD = 50


logger = logging.getLogger('django.db')


def _patched_execute(cursor, sql, params=None):
    cursor._qcm_callback_execute(sql, params)
    return cursor._qcm_original_execute(sql, params)

def _patched_executemany(cursor, sql, param_list):
    cursor._qcm_callback_executemany(sql, param_list)
    return cursor._qcm_original_executemany(sql, param_list)


class ConnectionCallbackMixin:
    def cursor(self, *args, **kwargs):
        cursor = super().cursor(*args, **kwargs)

        # make sure noone else has tried to patch execute()/executemany() on the object
        if cursor.__class__.executemany != cursor.executemany.__func__ or \
                        cursor.__class__.execute != cursor.execute.__func__:
            warnings.warn(
                "Connection '%s' cursor has already been patched; ConnectionCallbackMixin doing nothing" % self.alias,
                RuntimeWarning
            )
            return cursor

        cursor._qcm_callback_execute = self._qcm_callback_execute
        cursor._qcm_callback_executemany = self._qcm_callback_executemany
        cursor._qcm_original_execute = cursor.execute
        cursor._qcm_original_executemany = cursor.executemany

        cursor.execute = _patched_execute.__get__(cursor)
        cursor.executemany = _patched_executemany.__get__(cursor)

        return cursor


class QueryInterceptor:
    def __init__(self, callback_execute, callback_executemany, connection: object, alias: str):
        self.callback_execute = callback_execute
        self.callback_executemany = callback_executemany
        self.connection = connection
        self.alias = alias
        self.patched = None

    def __enter__(self):
        # we patch on the connection object itself; make sure there's nothing attached to the object
        if hasattr(self.connection, '_query_count_middleware') or isinstance(self.connection, ConnectionCallbackMixin):
            warnings.warn(
                "Connection '%s' has already been patched; has QueryCountMiddleware been included twice?" % self.alias,
                RuntimeWarning
            )
            return

        # TODO: At some point we might cache these generated classes so we don't have to recreate it every time
        original_class = self.connection.__class__
        PatchedConnectionClass = type(
            'QueryCountMiddleware' + original_class.__name__,
            (ConnectionCallbackMixin, original_class),
            {'_qcm_original_class': original_class},
        )

        self.connection.__class__ = PatchedConnectionClass
        self.patched = True
        self.connection._qcm_callback_execute =  self.callback_execute
        self.connection._qcm_callback_executemany = self.callback_executemany

    def __exit__(self, ex_type, ex_value, ex_trace):
        if not self.patched:
            # multiple QueryCountMiddleware present in MIDDLEWARE
            return

        if not isinstance(self.connection, ConnectionCallbackMixin):
            warnings.warn(
                "Connection '%s' has been unexpectedly changed; QueryCountMiddleware cannot cleanup" % self.alias,
                RuntimeWarning
            )
            return

        self.connection.__class__ = self.connection._qcm_original_class
        delattr(self.connection, '_qcm_callback_execute')
        delattr(self.connection, '_qcm_callback_executemany')


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
        # warnings.simplefilter('always', category=QueryCountWarning)

    def increment(self, *args, **kwargs):
        self.query_count += 1

    def __call__(self, request):
        self.query_count = 0

        # set up DB patching
        request.QUERY_COUNT_WARNING_THRESHOLD = getattr(settings, 'QUERY_COUNT_WARNING_THRESHOLD', DEFAULT_QUERY_COUNT_WARNING_THRESHOLD)

        with AllConnectionsInterceptor(self.increment, self.increment):
            response = self.get_response(request)

        if getattr(request, 'QUERY_COUNT_WARNING_THRESHOLD', 0) and self.query_count >= request.QUERY_COUNT_WARNING_THRESHOLD:
            logger.warning('Request ran %d queries', self.query_count)

        return response
