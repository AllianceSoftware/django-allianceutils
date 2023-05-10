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
import warnings

from django.conf import settings
from django.db import connection
from django.http import HttpRequest
from django.http import HttpResponse

DEFAULT_QUERY_COUNT_WARNING_THRESHOLD = 50

logger = logging.getLogger('django.db')


class QueryCounter:
    count: int

    def __init__(self):
        self.count = 0

    def __call__(self, execute, sql, params, many, context):
        self.count += 1
        return execute(sql, params, many, context)


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

        counter = QueryCounter()
        with connection.execute_wrapper(counter):
            response = self.get_response(request)
        query_count = counter.count

        if getattr(request, 'QUERY_COUNT_WARNING_THRESHOLD', 0) and query_count >= request.QUERY_COUNT_WARNING_THRESHOLD:
            logger.warning(f'excessive query count: request "{request.method} {request.path}" ran {query_count} queries')

        return response
