from django.db import connection


class QueryCountMiddleware(object):
    # prints a simple warning if number of queries executed exceeds set threshold
    # based on https://www.dabapps.com/blog/logging-sql-queries-django-13/
    # NOTE: Not included in Unit test - Django nose forces the DEBUG to be False thus the connection.queries in test will always be empty.
    #  - see: https://github.com/django-nose/django-nose/issues/160
    QUERY_WARNING_THRESHOLD = 40

    def process_response(self, request, response):
        executed = len(connection.queries)
        if executed > self.QUERY_WARNING_THRESHOLD:
            print(
                "\033[91mToo Many Queries: %s queries were executed for the last request. Can it be reduced?\033[0m" % (
                executed, self.QUERY_WARNING_THRESHOLD))
        return response
