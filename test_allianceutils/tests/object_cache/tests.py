
from django.test import Client
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from test_allianceutils.tests.object_cache.models import ObjectCacheTestModel


class ObjectCacheTestCase(TestCase):

    @override_settings(
        # we're counting queries and don't want any backends or middleware interfering
        AUTHENTICATION_BACKENDS=(),
        MIDDLEWARE=(),
    )
    def test_object_cache(self):
        client = Client()

        # Create a sample user for use as our test object
        object1 = ObjectCacheTestModel.objects.create(name='Hello World 1')
        path = reverse('object_cache:test_cache', kwargs={'pk': object1.id})

        with self.assertNumQueries(1):
            response = client.get(path=path, data={"count": 1})
        self.assertEqual(response.json()["items"], [[object1.pk, object1.name]] * 1)
        self.assertEqual(response.status_code, 200)

        with self.assertNumQueries(1):
            response = client.get(path=path, data={"count": 10})
        self.assertEqual(response.json()["items"], [[object1.pk, object1.name]] * 10)
        self.assertEqual(response.status_code, 200)

        # now try with a different object to make sure object1 isn't cached between requests
        object2 = ObjectCacheTestModel.objects.create(name='Hello World 2')
        path = reverse('object_cache:test_cache', kwargs={'pk': object2.id})

        with self.assertNumQueries(1):
            response = client.get(path=path, data={"count": 10})
        self.assertEqual(response.json()["items"], [[object2.pk, object2.name]] * 10)
        self.assertEqual(response.status_code, 200)
