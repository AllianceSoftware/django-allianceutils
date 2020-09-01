from django.conf.urls import url

from .views import CacheMixinViewset

app_name = 'object_cache'

urlpatterns = [
    url(r'^test_cache/(?P<pk>\d+)/$', CacheMixinViewset.as_view({'get': 'get'}), name="test_cache")
]
