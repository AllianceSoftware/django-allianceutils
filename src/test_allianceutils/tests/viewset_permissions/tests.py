try:
    import rest_framework
except ImportError:
    import unittest
    raise unittest.SkipTest("djangorestframework is not installed")

from decimal import Decimal
from typing import Optional
from typing import Set

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission
from django.db import transaction
from django.test import Client
from django.test import modify_settings
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from rest_framework import viewsets
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

from allianceutils.api.permissions import GenericDjangoViewsetPermissions
from test_allianceutils.tests.profile_auth.models import User
from test_allianceutils.tests.viewset_permissions.models import NinjaTurtleModel
from test_allianceutils.tests.viewset_permissions.models import SenseiRatModel
from test_allianceutils.tests.viewset_permissions.views import NinjaTurtleSerializer

USER_EMAIL = "test@example.com"
USER_PASS = "password"


class IgnoreObjectsBackend:
    """
    Django's ModelBackend will reject any object permission check with an object;
    we want to simply ignore objects instead.
    This should come last in the authentication backends list
    """
    def has_perm(self, user_obj, perm, obj=None):
        if obj is not None:
            return ModelBackend().has_perm(user_obj, perm, None)
        return None


@override_settings(
    MIDDLEWARE=(
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
    ),
    AUTHENTICATION_BACKENDS=(
        'django.contrib.auth.backends.ModelBackend',
    ),
)
class ViewsetPermissionsTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create(email=USER_EMAIL)
        self.user.set_password(USER_PASS)
        self.user.save()

        self.turtle = NinjaTurtleModel.objects.create(
            name="leonardo",
            color="red",
            shell_size=Decimal("12.1"),
        )

    def grant_permission(self, codename: str, model=NinjaTurtleModel):
        perm = Permission.objects.get_by_natural_key(
            codename=codename,
            app_label=model._meta.app_label,
            model=model._meta.model_name
        )
        self.user.user_permissions.add(perm)
        # refresh_from_db() doesn't refresh the user permissions cache, https://stackoverflow.com/a/68888245
        #  see _get_permissions() and get_all_permissions()
        #  in https://github.com/django/django/blob/main/django/contrib/auth/backends.py
        # self.user = User.objects.get(pk=self.user.pk)
        cache_attrs = [
            "_user_perm_cache",
            "_group_perm_cache",
            "_perm_cache",
        ]
        for attr in cache_attrs:
            try:
                delattr(self.user, attr)
            except AttributeError:
                pass

    def test_simple_permission_viewset(self):
        """
        Test SimpleDjangoObjectPermissions
        """
        client = Client()
        client.force_login(self.user)

        # request should not succeed
        response = client.get(reverse('permissions:simple-list'))
        self.assertEqual(response.status_code, 403)

        response = client.get(reverse('permissions:simple-detail', kwargs={"pk": self.turtle.id}))
        self.assertEqual(response.status_code, 403)

        # once you add the permission to that user it should now pass
        self.grant_permission("can_eat_pizza")

        response = client.get(reverse('permissions:simple-list'))
        self.assertEqual(response.status_code, 200)

        response = client.get(reverse('permissions:simple-detail', kwargs={"pk": self.turtle.id}))
        self.assertEqual(response.status_code, 200)

    @modify_settings(
        AUTHENTICATION_BACKENDS={
            "append": 'test_allianceutils.tests.viewset_permissions.tests.IgnoreObjectsBackend',
        }
    )
    def test_model_permission_viewset(self):
        """
        Test GenericDjangoViewsetPermissions
        """
        client = APIClient()
        client.force_login(self.user)

        def test_methods(with_grant_permission: Optional[str] = None, should_succeed: Set = set()):
            turtle_id = self.turtle.id

            with transaction.atomic():
                if with_grant_permission:
                    self.grant_permission(with_grant_permission)

                response = client.get(reverse('permissions:model-list'))
                self.assertEqual(response.status_code, 200 if "view" in should_succeed else 403)

                response = client.get(reverse('permissions:model-detail', kwargs={"pk": turtle_id}))
                self.assertEqual(response.status_code, 200 if "view" in should_succeed else 403)

                response = client.post(reverse('permissions:model-list'), data={"name": "leonardo", "color": "blue", "shell_size": "13.0"})
                self.assertEqual(response.status_code, 201 if "add" in should_succeed else 403)

                response = client.patch(reverse('permissions:model-detail', kwargs={"pk": turtle_id}), data={"name": "michaelangelo"})
                self.assertEqual(response.status_code, 200 if "change" in should_succeed else 403)

                response = client.delete(reverse('permissions:model-detail', kwargs={"pk": turtle_id}))
                self.assertEqual(response.status_code, 204 if "delete" in should_succeed else 403)

                transaction.set_rollback(True)

        test_methods()

        test_methods("view_ninjaturtlemodel", {"view"})

        test_methods("add_ninjaturtlemodel", {"add"})

        test_methods("change_ninjaturtlemodel", {"change"})

        test_methods("delete_ninjaturtlemodel", {"delete"})


    @modify_settings(
        AUTHENTICATION_BACKENDS={
            "append": 'test_allianceutils.tests.viewset_permissions.tests.IgnoreObjectsBackend',
        }
    )
    def test_get_model_permission_viewset(self):
        factory = APIRequestFactory()

        # These two ViewSets are equivalent; they just use different hooks to
        # return the model to use for permission checks
        class NinjaTurtleGetModelPermission1(GenericDjangoViewsetPermissions):
            def get_model(self, view):
                return SenseiRatModel

        class NinjaTurtleGetModelViewSet1(viewsets.ModelViewSet):
            queryset = NinjaTurtleModel.objects.all()
            serializer_class = NinjaTurtleSerializer

            permission_classes = [NinjaTurtleGetModelPermission1]

        class NinjaTurtleGetModelViewSet2(viewsets.ModelViewSet):
            queryset = NinjaTurtleModel.objects.all()
            serializer_class = NinjaTurtleSerializer

            permission_classes = [GenericDjangoViewsetPermissions]

            def get_permission_model(self):
                return SenseiRatModel


        def test_methods(with_grant_permission: Optional[str] = None, grant_model=NinjaTurtleModel,
                should_succeed: Set = set()):
            turtle_id = self.turtle.id
            for viewset in (NinjaTurtleGetModelViewSet1, NinjaTurtleGetModelViewSet2):
                with self.subTest(f"{viewset.__name__} with_grant_permission={with_grant_permission} grant_model={grant_model.__name__} should_success={should_succeed}"):
                    with transaction.atomic():
                        if with_grant_permission:
                            self.grant_permission(with_grant_permission, grant_model)
                        view = viewset.as_view({"get": "list"})
                        # Refetch user... something was caching permissions
                        user = User.objects.get(pk=self.user.pk)
                        request = factory.get("")
                        force_authenticate(request, user=user)
                        response = view(request).render()
                        self.assertEqual(response.status_code, 200 if "view" in should_succeed else 403)

                        view = viewset.as_view({"get": "retrieve"})
                        request = factory.get("")
                        force_authenticate(request, user=user)
                        response = view(request, pk=turtle_id).render()
                        self.assertEqual(response.status_code, 200 if "view" in should_succeed else 403)

                        transaction.set_rollback(True)

        test_methods()
        test_methods("view_ninjaturtlemodel")  # should fail; perm lookup would hit SenseiRat who is going to say no
        test_methods("view_senseiratmodel", SenseiRatModel, {"view"})  # should succeed with permission from SenseiRat


