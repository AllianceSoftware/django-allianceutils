try:
    import rest_framework
except ImportError:
    import unittest
    raise unittest.SkipTest("djangorestframework is not installed")

from django.test import TestCase
from rest_framework.serializers import ModelSerializer

from allianceutils.api import SerializerOptInFieldsMixin
from test_allianceutils.tests.profile_auth.models import User


class UserSerializer(SerializerOptInFieldsMixin, ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email", "is_active", "is_staff")
        opt_in_only_fields = ("is_active", "is_staff")


class MockRequest:
    def __init__(self, query_params):
        self.query_params = query_params


class OptinFieldMixinTestcase(TestCase):
    def test_no_opt_in_field_returned_by_default(self):
        context = {"request": MockRequest({})}
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" in serializer.fields)
        self.assertTrue("first_name" in serializer.fields)
        self.assertTrue("is_active" not in serializer.fields)
        self.assertTrue("is_staff" not in serializer.fields)

    def test_only_include_fields_specified_are_returned_single(self):
        context = {"request": MockRequest({"include_fields": "email"})}
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" in serializer.fields)
        self.assertTrue("first_name" not in serializer.fields)
        self.assertTrue("is_active" not in serializer.fields)
        self.assertTrue("is_staff" not in serializer.fields)

        context = {"request": MockRequest({"include_fields": "first_name"})}
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" not in serializer.fields)
        self.assertTrue("first_name" in serializer.fields)
        self.assertTrue("is_active" not in serializer.fields)
        self.assertTrue("is_staff" not in serializer.fields)

    def test_only_include_fields_specified_are_returned_multiple(self):
        context = {"request": MockRequest({"include_fields": "email,first_name"})}
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" in serializer.fields)
        self.assertTrue("first_name" in serializer.fields)
        self.assertTrue("is_active" not in serializer.fields)
        self.assertTrue("is_staff" not in serializer.fields)

    def test_only_include_fields_specified_are_returned_multiple_via_list_entry(self):
        context = {"request": MockRequest({"include_fields": ["email", "first_name"]})}
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" in serializer.fields)
        self.assertTrue("first_name" in serializer.fields)
        self.assertTrue("is_active" not in serializer.fields)
        self.assertTrue("is_staff" not in serializer.fields)

    def test_only_include_fields_specified_are_returned_multiple_via_mixed_entry(self):
        context = {
            "request": MockRequest(
                {"include_fields": ["email", "first_name,last_name"]}
            )
        }
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" in serializer.fields)
        self.assertTrue("first_name" in serializer.fields)
        self.assertTrue("last_name" in serializer.fields)
        self.assertTrue("is_active" not in serializer.fields)
        self.assertTrue("is_staff" not in serializer.fields)

    def test_only_include_fields_specified_are_returned_including_opt_in(self):
        context = {"request": MockRequest({"include_fields": "email,is_staff"})}
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" in serializer.fields)
        self.assertTrue("first_name" not in serializer.fields)
        self.assertTrue("is_active" not in serializer.fields)
        self.assertTrue("is_staff" in serializer.fields)

    def test_only_include_fields_specified_are_returned_including_opt_in_only(self):
        context = {"request": MockRequest({"include_fields": "is_staff"})}
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" not in serializer.fields)
        self.assertTrue("first_name" not in serializer.fields)
        self.assertTrue("is_active" not in serializer.fields)
        self.assertTrue("is_staff" in serializer.fields)

    def test_specify_one_opt_in_field(self):
        context = {"request": MockRequest({"opt_in_fields": "is_staff"})}
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" in serializer.fields)
        self.assertTrue("first_name" in serializer.fields)
        self.assertTrue("activated_at" not in serializer.fields)
        self.assertTrue("is_staff" in serializer.fields)

    def test_specify_multiple_opt_in_field(self):
        context = {"request": MockRequest({"opt_in_fields": "is_staff,is_active"})}
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" in serializer.fields)
        self.assertTrue("first_name" in serializer.fields)
        self.assertTrue("is_active" in serializer.fields)
        self.assertTrue("is_staff" in serializer.fields)

    def test_specify_optin_and_input_at_same_time(self):
        context = {
            "request": MockRequest(
                {"include_fields": "email", "opt_in_fields": "is_staff"}
            )
        }
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" in serializer.fields)
        self.assertTrue("first_name" not in serializer.fields)
        self.assertTrue("is_active" not in serializer.fields)
        self.assertTrue("is_staff" in serializer.fields)

    def test_directly_passing_via_context_also_works(self):
        context = {"include_fields": "email", "opt_in_fields": "is_staff"}
        serializer = UserSerializer(context=context)
        self.assertTrue("id" in serializer.fields)
        self.assertTrue("email" in serializer.fields)
        self.assertTrue("first_name" not in serializer.fields)
        self.assertTrue("is_active" not in serializer.fields)
        self.assertTrue("is_staff" in serializer.fields)
