import io
import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.core.management import call_command
from django.db import IntegrityError
from django.forms import IntegerField
from django.forms import ModelForm
from django.test import Client
from django.test import override_settings
from django.test import TestCase
from django.test.utils import isolate_apps
from django.urls import reverse
from django.utils.http import urlencode

from allianceutils.auth.models import GenericUserProfile
from allianceutils.auth.models import ID_ERROR_PROFILE_RELATED_TABLES

from .models import AdminProfile
from .models import CustomerProfile
from .models import User
from .models import UserFKImmediateModel
from .models import UserFKIndirectModel

try:
    import authtools
except ImportError:
    authtools = None


def _random_email_case(email: str) -> str:
    parts = email.split('@')
    mailbox, domain = '@'.join(parts[:-1]), parts[-1]
    mailbox = ''.join([
        c.lower() if random.getrandbits(1) else c.upper()
        for i, c in enumerate(mailbox)
    ])
    return f'{mailbox}@{domain}'

@override_settings(
    MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
    ],
    PASSWORD_HASHERS=(
        'django.contrib.auth.hashers.SHA1PasswordHasher',
    ),
    AUTHENTICATION_BACKENDS=(
        'allianceutils.auth.backends.ProfileModelBackend' if authtools else 'test_allianceutils.auth.backends.ProfileModelBackend',
    ),
)
class AuthTestCase(TestCase):
    def setUp(self):
        User.objects.all().delete()

        def create_user(model, username):
            # objects.create_user() is only available if UserManager inheritance works
            # w/ more recent authtools, you dont have username - instead you have your email
            # also, lets try to create user's email in a mIxEdCaSe in order to test whether its case sensitive or not
            email_mixed_case = _random_email_case(f'{username}@example.com')
            user = model(email=email_mixed_case)
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

        # also create referrer records
        # to keep things simple we use the same PKs as FKs
        # for profile_id in self.profiles:
        #     UserFKImmediateModel(pk=profile_id, fk=profile_id).save()
        #     UserFKIndirectModel(pk=profile_id, fk=profile_id).save()

    # number of queries if select_related() has been called to include profile tables
    SELECT_QUERY_COUNT = 1

    # number of queries of prefetch_related() has been called to include profile tables
    PREFETCH_QUERY_COUNT = 3

    def get_profile_query_count(self, user) -> int:
        """
        Return the number of expected queries to lookup a User's Profile if uncached
        """
        query_counts = {
            CustomerProfile: 1,
            AdminProfile: 2,
            User: 2,
        }
        return query_counts[type(self.profiles[user.id])]

    def test_iterate_user(self):
        """
        Iterating over users instantiates the correct type
        """
        with self.assertNumQueries(1):
            qs = User.objects.all().filter(id__gt=0).filter(id__isnull=False)
            for fetched in qs:
                with self.subTest(email=fetched.email):
                    self.assertEqual(User, type(fetched))
            self.assertEqual(qs.count(), len(self.profiles))

    def test_iterate_user_profile(self):
        """
        Iterating over users still allows us to (inefficiently) get profiles
        """
        qs = User.objects.all().filter(id__gt=0).filter(id__isnull=False)
        for fetched in qs:
            with self.subTest(email=fetched.email):
                self.assertEqual(User, type(fetched))
                with self.assertNumQueries(self.get_profile_query_count(fetched)):
                    profile = fetched.profile
                    self.assertEqual(type(self.profiles[fetched.id]), type(profile))

                    # should be cached
                    with self.assertNumQueries(0):
                        profile = fetched.profile
                        self.assertEqual(type(self.profiles[fetched.id]), type(profile))

        self.assertEqual(qs.count(), len(self.profiles))

    def test_iterate_profile(self):
        """
        Iterating over profiles instantiates the correct type
        """
        with self.assertNumQueries(1):
            # chain some random filters together
            qs = User.profiles.filter(id__gt=0).filter(id__isnull=False).all()
            for fetched in qs:
                with self.subTest(email=fetched.email):
                    self.assertEqual(type(self.profiles[fetched.id]), type(fetched))

                    profile = fetched.profile
                    self.assertEqual(type(self.profiles[fetched.id]), type(fetched))

            self.assertEqual(qs.count(), len(self.profiles))

    def test_get_user(self):
        """
        Fetching an individual user instantiates the correct type
        """
        for user_id, original_profile in self.profiles.items():
            with self.subTest(email=original_profile.email):
                with self.assertNumQueries(1):
                    fetched = User.objects.get(pk=user_id)
                    self.assertEqual(User, type(fetched))

                with self.assertNumQueries(1):
                    fetched = User.objects.all()[0]
                    self.assertEqual(User, type(fetched))

    def test_get_profile(self):
        """
        Fetching an individual profile instantiates the correct type
        """
        for user_id, original_profile in self.profiles.items():
            with self.subTest(email=original_profile.email):
                with self.assertNumQueries(1):
                    fetched = User.profiles.get(pk=user_id)
                    self.assertEqual(type(original_profile), type(fetched))

                with self.assertNumQueries(1):
                    fetched = User.profiles.all().filter(pk=user_id)[0]
                    self.assertEqual(type(original_profile), type(fetched))

    def test_get_profile_profile(self):
        """
        User().profile.profile.profile... works
        """
        for user_id, original_profile in self.profiles.items():
            manager_query_counts = (
                (User.objects,                    User, self.get_profile_query_count(original_profile)),
                (User.profiles,                   type(original_profile), 0),
            )

            if type(original_profile) != User:
                manager_query_counts += (
                    (type(original_profile).objects, type(original_profile), 0),
                    (type(original_profile).profiles, type(original_profile), 0),
                )

            for manager, expected_fetched_type, profile_lookup_query_count in manager_query_counts:
                with self.subTest(email=original_profile.email, model=manager.model.__name__, manager=manager.name):
                    # fetch record with no profile lookup
                    with self.assertNumQueries(1):
                        fetched = manager.get(pk=user_id)
                        self.assertEqual(expected_fetched_type, type(fetched))

                    # repeated profile lookups
                    with self.assertNumQueries(profile_lookup_query_count):
                        profile = fetched.profile.profile.profile.profile
                        self.assertEqual(type(original_profile), type(profile))

                    # repeated profile lookups, should be cached
                    with self.assertNumQueries(0):
                        profile = fetched.profile.profile.profile.profile
                        self.assertEqual(type(original_profile), type(profile))

                    # fetch record with no profile lookup (alternate method)
                    with self.assertNumQueries(1):
                        fetched = manager.filter(pk=user_id)[0]
                        self.assertEqual(expected_fetched_type, type(fetched))

                    # repeated profile lookups, should be cached
                    with self.assertNumQueries(profile_lookup_query_count):
                        profile = fetched.profile.profile.profile.profile
                        self.assertEqual(type(original_profile), type(profile))

                    # repeated profile lookups, should be cached
                    with self.assertNumQueries(0):
                        profile = fetched.profile.profile.profile.profile
                        self.assertEqual(type(original_profile), type(profile))

    def test_inherit_user_manager(self):
        """
        Manager should inherit from the base model manager
        """
        manager = User.objects
        user = manager.create_user(email='user99@example.com', password='abc123')
        self.assertEqual(type(user), User)
        self.assertIsNotNone(manager.get_by_natural_key('user99@example.com'))

        manager = User.objects
        user = manager.create_user(email='user100@example.com', password='abc123')
        self.assertEqual(type(user), User)
        self.assertIsNotNone(manager.get_by_natural_key('user100@example.com'))

        manager = User.profiles
        user = manager.create_user(email='user101@example.com', password='abc123')
        self.assertEqual(type(user), User)
        self.assertIsNotNone(manager.get_by_natural_key('user101@example.com'))

    def test_login(self):
        """
        Can login using user details
        """
        client = Client()

        for user in (self.user1, self.admin1, self.customer1):
            with self.subTest(email=user.email):
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
                    data={'username': user.email, 'password': 'badpassword'})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'This is a login page')

                # login page should succeed with a good password
                response = client.post(
                    path=login_page_url,
                    data={'username': user.email, 'password': 'abc123'},
                    follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'This is a protected page')
                self.assertContains(response, f'Username is {user.email}')

                # logout for the next user
                response = client.post(reverse('logout'))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'This is a logout page')

                # login page should succeed with a good password and case-alternated username eg. AdmIn1@eAmpLe.cOm
                email_mixed_case = _random_email_case(user.email)
                response = client.post(
                    path=login_page_url,
                    data={'username': email_mixed_case, 'password': 'abc123'},
                    follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'This is a protected page')
                self.assertContains(response, f'Username is {user.email}')

                # logout for the next user
                response = client.post(reverse('logout'))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'This is a logout page')

    def test_create_user_with_case_alternated_existing_username_should_fail(self):
        email_mixed_case = _random_email_case(self.user1.email)
        user = User(email=email_mixed_case)
        self.assertRaises(IntegrityError, user.save)

    def test_email_uniqueness_validation(self):
        class UserForm(ModelForm):
            class Meta:
                model = User
                fields = ("email", )

        username = self.user1.email.split('@')[0]
        username = ''.join([x.lower() if i%3 else x.upper() for i,x in enumerate(username)])
        form = UserForm(data={'email': f'{username}@example.com'})
        self.assertFalse(form.is_valid())
        self.assertEqual(set(form.errors.keys()), {"email"})
        form = UserForm(data={'email': 'available@example.com'})
        self.assertTrue(form.is_valid())


    def test_middleware(self):
        """
        Standard django middleware returns the right profile type
        """
        client = Client()

        for user in (self.user1, self.admin1, self.customer1):
            with self.subTest(email=user.email):
                # login page should succeed
                response = client.post(
                    path=reverse('login') + '?' + urlencode({'next': reverse('profile_auth:login_required')}),
                    data={'username': user.email, 'password': 'abc123'},
                    follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'This is a protected page')
                self.assertEqual(response.context['user']['id'], user.id)
                self.assertEqual(response.context['user']['username'], user.email)
                self.assertEqual(response.context['user']['class'], type(user).__name__)

                # logout for the next user
                response = client.post(reverse('logout'))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'This is a logout page')

    def _test_exception(self, exception_name, func):
        generic_exception = getattr(User, exception_name)
        user_exception = getattr(User, exception_name)
        self.assertTrue(issubclass(generic_exception, user_exception))

        tests = (
            (User, User.objects),
            (AdminProfile, AdminProfile.objects),
            (CustomerProfile, CustomerProfile.objects),
            (User, User.objects),
            (User, User.profiles),
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
        self._test_exception('DoesNotExist', lambda mgr: mgr.get_by_natural_key('thisshouldnotexist'))

    def test_exception_multipleobjectsreturned(self):
        self._test_exception('MultipleObjectsReturned', lambda mgr: mgr.get(email__isnull=False))

    def test_superuser_create(self):
        username = 'test_superuser_create'
        email = username + '@example.com'
        stdout = io.StringIO()
        try:
            call_command('createsuperuser',
                interactive=False,
                email=email,
                stdout=stdout
            )
        except Exception:
            stdout.seek(0)
            print(stdout.read())
            raise

        # validate that was created correctly
        manager = get_user_model()._default_manager

        user = manager.get(email=email)
        self.assertEqual(user.email, email)

        user = manager.get_by_natural_key(email)
        self.assertEqual(user.email, email)

    def test_fk_immediate(self):
        for user_id, original_profile in self.profiles.items():
            with self.subTest(email=original_profile.email):
                # can assign any User or subclass to the FK
                referrer = UserFKImmediateModel(fk_id=user_id)
                referrer.save()

                # when reloaded, returns the user class
                with self.assertNumQueries(1):
                    referrer = UserFKImmediateModel.objects.get(pk=referrer.id)
                with self.assertNumQueries(1):
                    fetched_user = referrer.fk
                self.assertIs(User, type(fetched_user))

                # extra queries to get the profile
                with self.assertNumQueries(self.get_profile_query_count(fetched_user)):
                    profile = fetched_user.profile
                self.assertIs(type(original_profile), type(profile))

    def test_fk_indirect(self):
        for user_id, original_profile in self.profiles.items():
            with self.subTest(email=original_profile.email):
                # can assign any User or subclass to the FK
                referrer_middle = UserFKImmediateModel(fk_id=user_id)
                referrer_middle.save()

                referrer = UserFKIndirectModel(fk_id=referrer_middle.id)
                referrer.save()

                # when reloaded, returns the user class
                with self.assertNumQueries(1):
                    referrer = UserFKIndirectModel.objects.get(pk=referrer.id)
                with self.assertNumQueries(2):
                    fetched_user = referrer.fk.fk
                self.assertIs(User, type(fetched_user))

                # extra queries to get the profile
                with self.assertNumQueries(self.get_profile_query_count(fetched_user)):
                    profile = fetched_user.profile
                self.assertIs(type(original_profile), type(profile))

    def test_select_prefetch_related(self):
        for user_id, original_profile in self.profiles.items():
            with self.subTest(email=original_profile.email):
                referrer_middle = UserFKImmediateModel(fk_id=user_id)
                referrer_middle.save()

                referrer = UserFKIndirectModel(fk_id=referrer_middle.id)
                referrer.save()

                def select_related(qs):
                    return User.objects.select_related_profiles(qs, 'fk__fk')

                def prefetch_related(qs):
                    return User.objects.prefetch_related_profiles(qs, 'fk__fk')

                operation_query_counts = (
                    # (lookup func, query count for SELECT, query count to get profile)
                    (lambda qs: qs.select_related('fk__fk')     .get(pk=referrer.id), 1, self.get_profile_query_count(original_profile)),
                    (lambda qs: select_related(qs)              .get(pk=referrer.id), 1, 0),
                    (lambda qs: qs.prefetch_related('fk__fk')   .get(pk=referrer.id), 3, self.get_profile_query_count(original_profile)),
                    (lambda qs: prefetch_related(qs)            .get(pk=referrer.id), 5, 0),
                )

                for i, (op_func, select_query_count, profile_query_count) in enumerate(operation_query_counts):
                    with self.subTest(i):
                        with self.assertNumQueries(select_query_count):
                            referrer = op_func(UserFKIndirectModel.objects)
                        with self.assertNumQueries(0):
                            fetched_user = referrer.fk.fk
                        self.assertIs(User, type(fetched_user))

                        with self.assertNumQueries(profile_query_count):
                            profile = fetched_user.profile
                        with self.assertNumQueries(0):
                            profile = profile.profile.profile
                        self.assertIs(type(original_profile), type(profile))

    def test_select_prefetch_related_profile(self):
        # select/prefetch_related_profiles() on User means no extra queries
        # select/prefetch_related_profiles() on something that's already a profile is a nooop

        model_tests = (
            # (model, query count for select_related(), query count for prefetch_related())
            (User, self.SELECT_QUERY_COUNT, self.PREFETCH_QUERY_COUNT),
            (AdminProfile, 1, 1),
            (CustomerProfile, 1, 1),
        )

        for model, select_query_count, prefetch_query_count in model_tests:
            with self.subTest(model=model.__name__):
                with self.assertNumQueries(select_query_count):
                    profiles = [u.profile for u in model.objects.select_related_profiles()]

                with self.assertNumQueries(prefetch_query_count):
                    profiles = [u.profile for u in model.objects.prefetch_related_profiles()]

    @isolate_apps('test_allianceutils.tests.profile_auth')
    def test_missing_related_profile_tables(self):
        class BadUserModel(GenericUserProfile, AbstractBaseUser):
            f = IntegerField()

            def get_full_name(self):
                return self.email

            def get_short_name(self):
                return self.email

        class GoodUserModel(GenericUserProfile, AbstractBaseUser):
            f = IntegerField()

            def get_full_name(self):
                return self.email

            def get_short_name(self):
                return self.email

            related_profile_tables = []

        errors_bad_user = BadUserModel.check()
        errors_good_user = GoodUserModel.check()

        self.assertEqual([err.id for err in errors_bad_user], [ID_ERROR_PROFILE_RELATED_TABLES, ID_ERROR_PROFILE_RELATED_TABLES])
        self.assertEqual(errors_good_user, [])

    def test_values(self):
        # You're not allowed to call values on a profile list
        qs = User.profiles.select_related_profiles()
        with self.assertRaises(ValueError):
            qs.values()

        with self.assertRaises(ValueError):
            qs.values_list()

    def test_count(self):
        # we don't do anything special with aggregate queries; they should work as normal
        self.assertEqual(User.profiles.count(), len(self.profiles))

    def test_queryset_with_args(self):
        self.assertEqual(tuple(AdminProfile.objects.all().values_list('email')), (('admin1@example.com',),('admin2@example.com',)))
        self.assertEqual(tuple(AdminProfile.objects.all().values_list('email', flat=True)), ('admin1@example.com', 'admin2@example.com'))
