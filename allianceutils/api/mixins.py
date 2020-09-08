from django.db import models


class CacheObjectMixin(object):
    """
    Cache get_object()

    Note that if you override get_object() this will only affect calls to super().get_object()
    """

    _cached_get_object: models.Model

    def get_object(self):
        if not hasattr(self, "_cached_get_object"):
            self._cached_get_object = super().get_object()
        return self._cached_get_object