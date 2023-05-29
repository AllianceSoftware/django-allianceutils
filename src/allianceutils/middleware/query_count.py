"""
Django DB instrumentation makes this relatively simple now:

https://docs.djangoproject.com/en/dev/topics/db/instrumentation/
"""
from __future__ import annotations

import logging
from typing import Callable
from typing import cast
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

    def __call__(self, execute: Callable, sql: str, params: dict, many, context):
        self.count += 1
        return execute(sql, params, many, context)


class QueryCountHttpRequest(HttpRequest):
    _querycountmiddleware: QueryCountMiddleware
    QUERY_COUNT_WARNING_THRESHOLD: int


class QueryCountMiddleware:
    get_response: Callable

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if getattr(request, '_querycountmiddleware', None) not in (None, self):
            msg = "QueryCountMiddleware appears to be already initialised (did you include QueryCountMiddleware multiple times?)"
            warnings.warn(msg, RuntimeWarning)
            return self.get_response(request)

        # we patch request to add some query count attributes
        request_qc = cast(QueryCountHttpRequest, request)

        # set this to avoid multiple QueryCountMiddlewares being included
        request_qc._querycountmiddleware = self
        request_qc.QUERY_COUNT_WARNING_THRESHOLD = getattr(
            settings,
            "QUERY_COUNT_WARNING_THRESHOLD",
            DEFAULT_QUERY_COUNT_WARNING_THRESHOLD)
        counter = QueryCounter()
        # request._query_counter = counter  # we expose this for testing
        with connection.execute_wrapper(counter):
            response = self.get_response(request_qc)

        if request_qc.QUERY_COUNT_WARNING_THRESHOLD and counter.count >= request_qc.QUERY_COUNT_WARNING_THRESHOLD:
            logger.warning(f"excessive query count: request '{request_qc.method} {request_qc.path}' ran {counter.count} queries")

        return response

    @classmethod
    def set_threshold(cls, request: HttpRequest, threshold: int):
        cast(QueryCountHttpRequest, request).QUERY_COUNT_WARNING_THRESHOLD = threshold

    @classmethod
    def increase_threshold(cls, request: HttpRequest, increment: int):
        cast(QueryCountHttpRequest, request).QUERY_COUNT_WARNING_THRESHOLD += increment