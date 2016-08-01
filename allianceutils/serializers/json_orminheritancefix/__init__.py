import django

# The ORM _meta changed in 1.9, this code only works with 1.8
if django.VERSION < (1, 8):
    raise Exception('json_orminheritancefix does not work with django < 1.8')
elif (1, 8) <= django.VERSION < (1, 9):
    from .json_orminheritancefix18 import Serializer
    from .json_orminheritancefix18 import Deserializer
elif (1, 9) <= django.VERSION < (1, 10):
    from .json_orminheritancefix19 import Serializer
    from .json_orminheritancefix19 import Deserializer
else:
    raise Exception('json_orminheritancefix has not been tested with django > 1.9')

__all_ = [
    'Deserializer',
    'Serializer',
]
