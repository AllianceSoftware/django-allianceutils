import warnings

import django

if django.VERSION < (1, 8):
    raise Exception('json_orminheritancefix does not work with django < 1.8')
elif (1, 8) <= django.VERSION < (1, 9): # The ORM _meta changed in 1.9, this code only works with 1.8
    from .json_orminheritancefix18 import Deserializer
    from .json_orminheritancefix18 import Serializer
elif (1, 9) <= django.VERSION < (1, 12): # Unit test passed for both 1.10 and 1.11
    from .json_orminheritancefix19 import Deserializer
    from .json_orminheritancefix19 import Serializer
elif (1, 12) <= django.VERSION < (2, 1):
    raise Exception('json_orminheritancefix has not been tested with django 2.0')
else:
    warnings.warn('json_orminheritancefix is not needed in django >=2.1 and will be removed', DeprecationWarning)
    from django.core.serializers.json import Deserializer
    from django.core.serializers.json import Serializer

__all_ = [
    'Deserializer',
    'Serializer',
]
