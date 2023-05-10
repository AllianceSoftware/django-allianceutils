import collections

import django.core.serializers.json
import django.utils.six as six


class Serializer(django.core.serializers.json.Serializer):
    """
    A version of django's core json serializer that outputs field in sorted order
    (the built-in one uses a standard dict() with completely unpredictable order
    which makes fixture diffs often contain field ordering changes)
    """
    def end_object(self, obj):
        self._current = collections.OrderedDict(sorted(six.iteritems(self._current)))
        super(Serializer, self).end_object(obj)
