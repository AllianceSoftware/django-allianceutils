from collections import OrderedDict
from typing import Any

import django.core.serializers.json


class Serializer(django.core.serializers.json.Serializer):
    """
    A version of django's core json serializer that outputs field in sorted order
    (the built-in one uses a standard dict() with completely unpredictable order
    which makes fixture diffs often contain field ordering changes)
    """
    _current: OrderedDict[Any, Any]  # is dict on parent but we replace with OrderedDict

    def end_object(self, obj):
        self._current = OrderedDict(sorted(self._current.items()))
        super(Serializer, self).end_object(obj)
