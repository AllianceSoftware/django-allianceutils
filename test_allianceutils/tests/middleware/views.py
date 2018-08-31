from django.db import connection
from django.http import HttpRequest
from django.http import HttpResponse


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

    if 'set_threshold' in request.POST:
        request.QUERY_COUNT_WARNING_THRESHOLD = int(request.POST['set_threshold'] or 0)

    for i in range(count):
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')

    return HttpResponse('Ran %d queries' % count)
