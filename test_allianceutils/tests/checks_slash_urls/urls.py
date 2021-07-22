from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from test_allianceutils.tests.checks_slash_urls.views import null_view

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
