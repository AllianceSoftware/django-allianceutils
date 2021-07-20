from distutils.util import strtobool
import threading
from time import sleep
from typing import Optional

from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.test.utils import CaptureQueriesContext

_request_thread_wait_barrier: Optional[threading.Barrier] = None


def reset_thread_wait_barrier(thread_count: int):
    """
    Causes all requests to the `run_queries` to pause before the end of the request and wait until `thread_count`
    requests have been made

    If thread_count is zero then aborts any existing thread waits and disables for future threads
    """
    global _request_thread_wait_barrier
    if _request_thread_wait_barrier is not None:
        _request_thread_wait_barrier.abort()
    if thread_count:
        _request_thread_wait_barrier = threading.Barrier(thread_count, timeout=10)
    else:
        _request_thread_wait_barrier = None


def run_queries(request: HttpRequest, **kwargs) -> HttpRequest:
    """
    Run a specified number of queries

    If reset_thread_wait_barrier() has been called, will pause before the end of the request until `thread_count`
    number of requests have been issued simultaneously

    POST vars:
        count: number of queries to run
        set_threshold: (optional) set request.QUERY_COUNT_WARNING_THRESHOLD to this value
    """
    count = int(request.POST['count'])
    throw_exception = strtobool(request.POST['throw_exception'])

    if 'set_threshold' in request.POST:
        request.QUERY_COUNT_WARNING_THRESHOLD = int(request.POST['set_threshold'] or 0)

    with connection.cursor() as cursor:
        for i in range(count):
            cursor.execute('SELECT 1')

    global _request_thread_wait_barrier
    if _request_thread_wait_barrier is not None:
        _request_thread_wait_barrier.wait()

    if throw_exception:
        # note that django test client only handles some exceptions:
        # https://docs.djangoproject.com/en/stable/topics/testing/tools/#exceptions
        raise PermissionDenied('throw_exception is True')

    return HttpResponse('Ran {count} queries')


def query_overhead(request: HttpRequest, **kwargs) -> HttpResponse:
    """
    Django will do things like 'SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED' at the start
    of a new connection to put the database connection in a consistent state

    This returns the number of queries executed for a request that does nothing except create a connection
    """
    with CaptureQueriesContext(connection) as cqc:
        # run at least one real query to ensure django has instantiated the connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')

    # django 1.11 and 2.1 behaviour is different; this method of calculating overhead appears to work:
    overhead = cqc.final_queries - 1
    return JsonResponse({'data': overhead})


def current_user(request: HttpRequest, **kwargs) -> HttpResponse:
    """
    returns current user from middleware
    """
    from allianceutils.middleware import CurrentUserMiddleware
    user = CurrentUserMiddleware.get_user()
    sleep(1)
    if user['user_id']:
        from django.contrib.auth import get_user_model
        return JsonResponse({'username': get_user_model().objects.get(id=user['user_id']).email})
    return JsonResponse({'username': None})
