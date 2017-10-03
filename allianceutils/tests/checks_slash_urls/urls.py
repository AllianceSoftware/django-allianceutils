from django.conf.urls import include
from django.conf.urls import url


def view(*args, **kwargs):
    pass


urlpatterns = [
    url(r'^noslash1$', view, name='no_url_view'),
    url(r'^prefix1/$', include([
        url(r'^slash1/$', view, name='no_url_view'),
        url(r'^noslash2$', view, name='no_url_view'),
        url(r'^prefix2/$', include([
            url(r'^slash2/$', view, name='no_url_view'),
            url(r'^noslash3$', view, name='no_url_view'),
        ])),
    ])),
]
