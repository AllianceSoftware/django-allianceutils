from django.conf import settings
from django.conf.urls import include
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin


def view(*args, **kwargs):
    pass


urlpatterns = [
    url(r'^ignoreme', view, name='no_url_view'),
    url(r'^noslash1$', view, name='no_url_view'),
    url(r'^prefix1/$', include([
        url(r'^$', view, name='no_url_view'),
        url(r'^slash1/$', view, name='no_url_view'),
        url(r'^noslash2$', view, name='no_url_view'),
        url(r'^prefix2/$', include([
            url(r'^$', view, name='no_url_view'),
            url(r'^slash2/$', view, name='no_url_view'),
            url(r'^noslash3$', view, name='no_url_view'),
        ])),
    ])),
    url(r'^admin/', admin.site.urls),
]

urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
