from django.db import connection
from django.http import HttpRequest
from django.http import HttpResponse


def run_queries(request: HttpRequest, **kwargs):
    count = int(request.POST['count'])

    if 'set_threshold' in request.POST:
        request.QUERY_COUNT_WARNING_THRESHOLD = int(request.POST['set_threshold'] or 0)

    for i in range(count):
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')

    return HttpResponse('Ran %d queries' % count)
