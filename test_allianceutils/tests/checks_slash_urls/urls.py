from django.conf import settings
from django.conf.urls import include
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin

from test_allianceutils.tests.checks_slash_urls.views import null_view

urlpatterns = [
    url(r'^ignoreme', null_view, name='no_url_view'),
    url(r'^noslash1$', null_view, name='no_url_view'),
    url(r'^prefix1/$', include([
        url(r'^$', null_view, name='no_url_view'),
        url(r'^slash1/$', null_view, name='no_url_view'),
        url(r'^noslash2$', null_view, name='no_url_view'),
        url(r'^prefix2/$', include([
            url(r'^$', null_view, name='no_url_view'),
            url(r'^slash2/$', null_view, name='no_url_view'),
            url(r'^noslash3$', null_view, name='no_url_view'),
        ])),
    ])),
    url(r'^admin/', admin.site.urls),
]

urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))

try:
    from rest_framework import routers
except ImportError:
    pass
else:
    from test_allianceutils.tests.checks_slash_urls.views_drf import FooViewSet

    # Check DRF router-generated URLs
    router = routers.DefaultRouter(trailing_slash=True)
    router.include_format_suffixes = False
    router.register(r'api/slash', FooViewSet)
    urlpatterns.extend(router.urls)

    router = routers.DefaultRouter(trailing_slash=False)
    router.include_format_suffixes = False
    router.register(r'api/noslash', FooViewSet)
    urlpatterns.extend(router.urls)
