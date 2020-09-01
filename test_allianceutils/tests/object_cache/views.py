from django.http import HttpRequest
from django.http import JsonResponse
from rest_framework.viewsets import ModelViewSet

from allianceutils.api.mixins import CacheObjectMixin
from test_allianceutils.tests.object_cache.models import ObjectCacheTestModel


class CacheMixinViewset(CacheObjectMixin, ModelViewSet):
    queryset = ObjectCacheTestModel.objects.all()

    def get(self, request: HttpRequest, pk):
        items = []
        for item in range(int(request.GET['count'])):
            obj = self.get_object()
            items.append((obj.pk, obj.name))

        return JsonResponse({'items': items})
