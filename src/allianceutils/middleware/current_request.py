from collections.abc import Callable
import threading

from django.http import HttpRequest
from django.http import HttpResponse

GLOBAL_REQUEST = threading.local()


class CurrentRequestMiddleware(object):
    """Provides access to the current request object

    To setup add ``common_lib.middleware.CurrentRequestMiddleware`` to :setting:`MIDDLEWARE`

    Usage::

        CurrentRequestMiddleware.get_request()
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not hasattr(GLOBAL_REQUEST, "request"):
            GLOBAL_REQUEST.request = []
        GLOBAL_REQUEST.request.append(request)
        try:
            return self.get_response(request)
        finally:
            GLOBAL_REQUEST.request.pop()

    @staticmethod
    def get_request() -> HttpRequest | None:
        """Get the current request

        If no request available returns None
        """
        try:
            return GLOBAL_REQUEST.request[-1]
        except (AttributeError, IndexError):
            return None
