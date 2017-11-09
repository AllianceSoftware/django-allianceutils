from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.utils.http import urlencode

from .models import AdminProfile
from .models import CustomerProfile
from .models import GenericUserProfile
from .models import User


@override_settings(
    MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
    ],
    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.UnsaltedSHA1PasswordHasher',
    )
)
class AuthTestCase(TestCase):
    def setUp(self):
        def create_user(model, username):
            # objects.create_user() is only available if UserManager inheritance works
            user = model(username=username, email='%s@example.com' % username)
            user.set_password('abc123')
            user.save()
            return user

        self.user1 = create_user(User, 'user1')
        self.admin1 = create_user(AdminProfile, 'admin1')
        self.customer1 = create_user(CustomerProfile, 'customer1')
        self.customer2 = create_user(CustomerProfile, 'customer2')
        self.admin2 = create_user(AdminProfile, 'admin2')

        self.profiles = {
            self.user1.id: self.user1,
            self.customer1.id: self.customer1,
            self.customer2.id: self.customer2,
            self.admin1.id: self.admin1,
            self.admin2.id: self.admin2,
        }

    @staticmethod
    def expected_class(profile, use_proxy):
        expected = profile.__class__
        if type(profile) is User and use_proxy:
            expected = GenericUserProfile
        return expected

    def test_profile_iterate_noproxy(self):
        """
        Iterating over users instantiates the correct profile type (original User model)
        """
        with self.assertNumQueries(1):
            qs = GenericUserProfile.objects_noproxy.all().filter(id__gt=0).filter(id__isnull=False)
            for fetched in qs:
                self.assertEqual(self.expected_class(self.profiles[fetched.id], use_proxy=False), fetched.__class__)
            self.assertEqual(qs.count(), len(self.profiles))

    def test_profile_iterate_proxy(self):
        """
        Iterating over users instantiates the correct profile type (proxied User model)
        """
        with self.assertNumQueries(1):
            qs = GenericUserProfile.objects_proxy.all().filter(id__gt=0).filter(id__isnull=False)
            for fetched in qs:
                self.assertEqual(self.expected_class(self.profiles[fetched.id], use_proxy=True), fetched.__class__)
            self.assertEqual(qs.count(), len(self.profiles))

    def test_profile_get_noproxy(self):
        """
        Fetching an individual record instantiates the correct profile (original user model)
        """
        for id, record in self.profiles.items():
            with self.assertNumQueries(1):
                fetched = GenericUserProfile.objects_noproxy.get(pk=id)
            self.assertEqual(self.expected_class(self.profiles[fetched.id], use_proxy=False), fetched.__class__)

    def test_profile_get_proxy(self):
        """
        Fetching an individual record instantiates the correct profile (proxied user model)
        """
        for id, record in self.profiles.items():
            with self.assertNumQueries(1):
                fetched = GenericUserProfile.objects_proxy.get(pk=id)
            self.assertEqual(self.expected_class(self.profiles[fetched.id], use_proxy=True), fetched.__class__)

    def test_inherit_user_manager(self):
        """
        Manager should inherit from the base model manager
        """
        manager = User.objects
        user = manager.create_user(username='user99', email='user99@example.com', password='abc123')
        self.assertEqual(user.__class__, User)
        self.assertIsNotNone(manager.get_by_natural_key('user99'))

        manager = GenericUserProfile.objects_noproxy
        user = manager.create_user(username='user100', email='user100@example.com', password='abc123')
        self.assertEqual(user.__class__, GenericUserProfile)
        self.assertIsNotNone(manager.get_by_natural_key('user100'))

        manager = GenericUserProfile.objects_proxy
        user = manager.create_user(username='user101', email='user101@example.com', password='abc123')
        self.assertEqual(user.__class__, GenericUserProfile)
        self.assertIsNotNone(manager.get_by_natural_key('user101'))

    def test_login(self):
        """
        Can login using user details
        """
        client = Client()

        for user in (self.user1, self.admin1, self.customer1):
            # protected page should redirect to login page
            response = client.get(
                path=reverse('profile_auth:login_required'),
                follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'This is a login page')

            login_page_url = response.redirect_chain[-1][0]

            # login page should fail with a bad password
            response = client.post(
                path=login_page_url,
                data={'username': user.username, 'password': 'badpassword'})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'This is a login page')

            # login page should succeed with a good password
            response = client.post(
                path=login_page_url,
                data={'username': user.username, 'password': 'abc123'},
                follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'This is a protected page')
            self.assertContains(response, 'Username is %s' % user.username)

            # logout for the next user
            response = client.get(reverse('logout'))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'This is a logout page')

    def test_middleware(self):
        """
        Standard django middleware returns the right profile type
        """
        client = Client()

        for user in (self.user1, self.admin1, self.customer1):
            # login page should succeed
            response = client.post(
                path=reverse('login') + '?' + urlencode({'next': reverse('profile_auth:login_required')}),
                data={'username': user.username, 'password': 'abc123'},
                follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'This is a protected page')
            self.assertContains(response, 'Username is %s' % user.username)
            self.assertContains(response, 'User class is %s' % user.__class__.__name__)

            # logout for the next user
            response = client.get(reverse('logout'))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'This is a logout page')

    def _test_exception(self, exception_name, func):
        generic_exception = getattr(GenericUserProfile, exception_name)
        user_exception = getattr(User, exception_name)
        self.assertTrue(issubclass(generic_exception, user_exception))

        tests = (
            (User, User.objects),
            (AdminProfile, AdminProfile.objects),
            (CustomerProfile, CustomerProfile.objects),
            (GenericUserProfile, GenericUserProfile.objects_noproxy),
            (GenericUserProfile, GenericUserProfile.objects_proxy),
        )

        for model, manager in tests:
            exception = getattr(model, exception_name)

            # models should always raise the correct exception
            with self.assertRaises(exception):
                func(manager)

            # which should also always be a subclass of user_exception
            with self.assertRaises(user_exception):
                func(manager)

    def test_exception_doesnotexist(self):
        self._test_exception('DoesNotExist', lambda mgr: mgr.get_by_natural_key('thisshoudlnotexist'))

    def test_exception_multipleobjectsreturned(self):
        self._test_exception('MultipleObjectsReturned', lambda mgr: mgr.get(username__isnull=False))

    def test_superuser_create(self):
        username = 'test_superuser_create'
        email = username + '@example.com'
        call_command('createsuperuser',
            interactive=False,
            username=username,
            email=email,
            #stdout=StringIO()
        )

        # validate that was created correctly
        manager = get_user_model()._default_manager

        user = manager.get(username=username)
        self.assertEqual(user.email, email)

        user = manager.get_by_natural_key(username)
        self.assertEqual(user.email, email)
