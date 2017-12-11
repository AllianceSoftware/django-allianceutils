from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from .models import Foo


class FooSerializer(ModelSerializer):
    class Meta:
        model = Foo
        fields = '__all__'


class FooViewSet(ModelViewSet):
    serializer_class = FooSerializer
    queryset = Foo.objects.all()


def null_view(*args, **kwargs):
    pass
