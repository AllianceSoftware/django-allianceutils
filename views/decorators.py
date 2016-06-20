from functools import wraps

from django.conf import settings
from django.utils.decorators import available_attrs
from django.views.decorators.gzip import gzip_page


def gzip_page_ajax(func):
    """
    Smarter version of django's gzip_page:
    - If settings.DEBUG not set, will always gzip
    - If settings.DEBUG set, will gzip only if request is an ajax request
    This allows you to use django-debug-toolbar in DEBUG mode (if you gzip a response then the debug toolbar middleware won't run)
    """
    gzipped_func = gzip_page(func)

    if not settings.DEBUG:
        return gzipped_func

    @wraps(func, assigned=available_attrs(func))
    def conditional_gzip_func(request, *args, **kwargs):
        if request.is_ajax():
            return gzipped_func(request, *args, **kwargs)
        return func(request, *args, **kwargs)
    return conditional_gzip_func
