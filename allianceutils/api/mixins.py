class CacheObjectMixin(object):
    """
    Cache get_object() on the request
    """
    def get_object(self):
        if not hasattr(self.request, '_cached_view_object'):
            self.request._cached_view_object = super(CacheObjectMixin, self).get_object()
        return self.request._cached_view_object
