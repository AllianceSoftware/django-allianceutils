import django
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin

from test_allianceutils.tests.checks_slash_urls.views import null_view

# We test old-style URLs by virtue of the fact that tox runs tests on both >=2.0 and <2.0 code
# TODO: When we drop support for django <2.0, need to make sure we still test old-style URLs
if django.VERSION >= (2, 0):
    from django.urls import path
    urlpatterns = [
        path(r'ignoreme-simplified', null_view, name='no_url_view'),
        path(r'noslash1', null_view, name='no_url_view'),
        path(r'prefix1/', include([
            path(r'', null_view, name='no_url_view'),
            path(r'slash1/', null_view, name='no_url_view'),
            path(r'noslash2', null_view, name='no_url_view'),
            path(r'prefix2/', include([
                path(r'', null_view, name='no_url_view'),
                path(r'slash2/', null_view, name='no_url_view'),
                path(r'noslash3', null_view, name='no_url_view'),
            ])),
        ])),
        path(r'^admin/', admin.site.urls),
    ]
else:
    from django.conf.urls import url
    urlpatterns = [
        url(r'^ignoreme-regex', null_view, name='no_url_view'),
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
