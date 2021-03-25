from rest_framework import serializers
from rest_framework import viewsets

from allianceutils.api.permissions import GenericDjangoViewsetPermissions
from allianceutils.api.permissions import SimpleDjangoObjectPermissions
from test_allianceutils.tests.viewset_permissions.models import NinjaTurtleModel
from test_allianceutils.tests.viewset_permissions.models import SenseiRatModel


class NinjaTurtleSerializer(serializers.ModelSerializer):
    class Meta:
        model = NinjaTurtleModel
        fields = '__all__'


class SimpleTestViewSet(viewsets.ModelViewSet):
    queryset = NinjaTurtleModel.objects.all()
    serializer_class = NinjaTurtleSerializer

    permission_classes = [SimpleDjangoObjectPermissions]
    permission_required = "viewset_permissions.can_eat_pizza"


class NinjaTurtleViewSet(viewsets.ModelViewSet):
    queryset = NinjaTurtleModel.objects.all()
    serializer_class = NinjaTurtleSerializer

    permission_classes = [GenericDjangoViewsetPermissions]

