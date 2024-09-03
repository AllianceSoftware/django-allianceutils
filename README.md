# Alliance Utils

![CI Tests](https://github.com/AllianceSoftware/django-allianceutils/workflows/Django%20CI/badge.svg)

A collection of utilities for django projects from [Alliance Software](https://www.alliancesoftware.com.au/).

* [Installation](#installation)
* [Usage](#usage)
    * [API](#api)
    * [Auth](#auth)
    * [Decorators](#decorators)
    * [Management](#management)
        * [Commands](#commands)
        * [Checks](#checks)
    * [Middleware](#middleware)
    * [Migrations](#migrations)
    * [Models](#models)
    * [Rules](#rules)
    * [Serializers](#serializers)
    * [Template](#template)
    * [Template Tags](#template-tags)
    * [Tests](#tests)
    * [Util](#util)
* [Changelog](#changelog)

## Installation

`pip install django-allianceutils`

## System Requirements

* Tested with django 4.2 and 5.0
  * Pull requests accepted for other versions, but at minimum we test against current LTS versions
* Python >=3.8

## Usage

### API

#### Mixins

##### SerializerOptInFieldsMixin

Regulates fields exposed on a Serializer by default & as requested based on query parameters or context.

* Pass 'include_fields' / 'opt_in_fields' thru query params or context to use.
* multiple fields can either be separated by comma
  eg, `/?include_fields=first_name,email&opt_in_fields=gait_recognition_prediction`
* or passed in the traditional list fashion
  eg, `/?include_fields=first_name&include_fields=email&opt_in_fields=gait_recognition_prediction`
* or mixed eg, `/?include_fields=first_name,email&include_fields=boo`
* By default, all "fields" defined in serializer, minus those listed in "opt_in_fields" would be returned.
* If "include_fields" is supplied, only fields requested this way would be returned.
* If "opt_in_fields" is supplied, fields requested this way PLUS fields from #1 or #2 would be returned.
* Pinned fields are always returned (defaults to primary key)

Usage:

```python
class UserSerializer(SerializerOptInFieldsMixin, ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "region",
            "activated_at",
            "is_staff",
        )
        # These fields only returned if explicitly requested
        opt_in_only_fields = ["activated_at", "is_staff"]
```

#### Permissions

##### register_custom_permissions

* Creates permissions that have no model by linking them to an empty content type
* Django creates permissions as part of
  the [`post_migrate` signal](https://docs.djangoproject.com/en/stable/ref/signals/#post-migrate)

Usage

```python
def on_post_migrate(sender, **kwargs):
    register_custom_permissions("myapp", ("my_perm", "My Permission"))
```

##### SimpleDjangoObjectPermissions

Permission class for Django Rest Framework that adds support for object level permissions.

Differs from just DRF's [DjangoObjectPermissions](https://www.django-rest-framework.org/api-guide/permissions/#object-level-permissions) because it
* does not require a queryset
* uses the same permission for every request http method and ViewSet method

Notes
* The default django permissions system will [always return False](https://docs.djangoproject.com/en/stable/topics/auth/customizing/#handling-object-permissions) if given an object; you must be using another permissions backend
* As per [DRF documentation](http://www.django-rest-framework.org/api-guide/permissions/#object-level-permissions): get_object() is only required if you want to implement object-level permissions
* **WARNING** If you override `get_object()` then you need to *manually* invoke `self.check_object_permissions(self.request, obj)`
* Will attempt to check permission both globally and on a per-object basis but considers it an error if the check returns True for both
*

Usage
* See [DRF permissions policy](https://www.django-rest-framework.org/api-guide/permissions/#setting-the-permission-policy) for details on apply Permissions policies globally

* To apply to a specific view you need to set `permission_required`
```python
class MyAPIView(SimpleDjangoObjectPermissions, APIView):
        permission_required = 'my_module.my_permission'
        permission_classes = [allianceutils.api.permissions.SimpleDjangoObjectPermissions]
```

If you have no object level permissions (eg. from rules) then it will just do a static permission check.

##### GenericDjangoViewsetPermissions

* Map viewset actions to Django permissions.
  * The model used for permission is extracted from the ViewSet
    * If you implement `get_permission_model` on the ViewSet that will be used
    * Otherwise it will call `get_queryset` on the ViewSet and extract the model from the returned queryset
 * To alter this behaviour extends `GenericDjangoViewsetPermissions` and implement `get_model`
* Usage example:
```python
class MyViewSet(GenericDjangoViewsetPermissions, viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MySerializer
```
* `GenericDjangoViewsetPermissions.default_actions_to_perms_map` defines the default set of permissions. These can be extended or overridden using `actions_to_perms_map`:
```python
class MyViewSet(GenericDjangoViewsetPermissions, viewsets.ModelViewSet):

    # ...

    actions_to_perms_map = {
        'create': []
    }
```
* No permissions will be required for the create action, but permissions for other actions will remain unchanged.
* By default permissions checks are passed the relevant model instance for per-object permission checks
    * This assumes that your backend doesn't ignore the model object (default django permissions simply ignore any object passed to a permissions check)
    * Since there is no model object, functions decorated with `@list_route` will pass `None` as the permissions check object

#### Parsers

##### CamelCaseJSONParser

Parser that recursively turns camelcase keys into underscored keys for JSON data.
This can be set globally on the [DEFAULT_PARSER_CLASSES](https://www.django-rest-framework.org/api-guide/settings/#default_parser_classes)
setting or on a ViewSet on the `parser_classes` property.

##### CamelCaseMultiPartJSONParser

Parser that recursively turns camelcase keys into underscored keys for JSON data and handles file uploads.
This parser supports receiving JSON data where a field value anywhere in the structure can be a file.
This is achieved on the frontend by converting a structure like:

```js
{
    name: 'Test',
    photo: File,
}
```

And converting it to

```js
{
    name: 'Test',
    photo: '____ATTACHED_FILE_ID_1',
}
```

This is then set on a field `jsonData` and the file is set on `____ATTACHED_FILE_ID_1` and submitted
as multipart.
This parser then handles parsing the JSON data into a dict and setting each attached file on the
correct key in the dict.
Note that this works with nested data (ie. any File anywhere in a nested JSON structure is supported).
To activate this behaviour the `X-MultiPart-JSON` header must be set to '1' or 'true'. If this header
is not set it falls back to the default behaviour of MultiPartParser
This can be set globally on the [DEFAULT_PARSER_CLASSES](https://www.django-rest-framework.org/api-guide/settings/#default_parser_classes)
setting or on a ViewSet on the `parser_classes` property.
Example frontend code to activate:
```js
let fileCount = 0;
const files = {};
const replacer = (key, value) => {
    if (value instanceof File) {
        const id = `____ATTACHED_FILE_ID_${fileCount++}`;
        files[id] = value;
        return id;
    }
    return value;
};
const stringifiedData = JSON.stringify(data, replacer);
const body = new FormData();
const body.append('jsonData', stringifiedData);
for (const [fileKey, file] of Object.entries(files)) {
    body.append(fileKey, file);
}
// eg. using a presto Endpoint
await myEndpoint.execute({
    body,
    headers: {
        // Remove default content type from endpoint (eg. json)
        'Content-Type': undefined,
        'X-MultiPart-JSON': true,
    },
});
```

#### Renderers

##### CamelCaseJSONRenderer

Renderer that recursively turns underscore-cased keys into camel-cased keys.
This can be set globally on the [DEFAULT_RENDERER_CLASSES](https://www.django-rest-framework.org/api-guide/settings/#default_renderer_classes)
setting or on a ViewSet on the `renderer_classes` property.

### Auth

#### MinimalModelBackend

* `allianceutils.auth.backends.MinimalModelBackend`
    * Replaces the built-in django [ModelBackend](https://docs.djangoproject.com/en/stable/ref/contrib/auth/#django.contrib.auth.backends.ModelBackend)
    * Provides django model-based authentication
    * Removes the default authorization (permissions checks) except for checking `is_superuser`

#### ProfileModelBackend

* Backends for use with [GenericUserProfile](#GenericUserProfile); see code examples there
* `allianceutils.auth.backends.ProfileModelBackendMixin` - in combo with [AuthenticationMiddleware](https://docs.djangoproject.com/en/stable/ref/middleware/#django.contrib.auth.middleware.AuthenticationMiddleware) will set user profiles on `request.user`
  * If you want
      * ~`allianceutils.auth.backends.ProfileModelBackend`~ - convenience class combined with case insensitive username & default django permissions backend
          * this depended on [`authtools`](https://django-authtools.readthedocs.io/en/latest/) which appears to have been
            abandoned and does not work with django >= 3.
            If using django 3 then we recommended that you create your own backend in your app:
            ```python
              class ProfileModelBackend(ProfileModelBackendMixin, MinimalModelBackend):
                  # you'll need to implement case insensitivity either here or in the User Model
                  pass
            ```

#### Permissions

##### NoDefaultPermissionsMeta

- Define a `Meta` class with empty default permissions so Django doesn't create any
- Usage example:

```python
class User(GenericUserProfile):

    class Meta(NoDefaultPermissionsMeta):
        pass
```

##### PermissionNotImplementedError

- Subclass of `NotImplementedError` specific to permissions

##### identify_global_perms

- Takes a permission or list of permissions and splits them into global and object permissions, returning a tuple of (global permission list, object permission list). If the type can't be determined, the permission is returned in the global permission list.

##### AmbiguousGlobalPermissionWarning

- Raised if a permission cannot be classified as either global or per-object

##### reverse_if_probably_allowed

- Attempts to guess whether a user has permission to access a view to determine whether a URL should be displayed. Only for display purposes, not actual security, as it is not 100% reliable: can be used to, for example, hide the edit link in a CRUD view where the user does not have edit access. Takes the current request and the requested viewname, and optionally the specific object to be accessed.

### Decorators

#### gzip_page_ajax

* Smarter version of django's [gzip_page](https://docs.djangoproject.com/en/stable/topics/http/decorators/#django.views.decorators.gzip.gzip_page):
    * If settings.DEBUG not set, will always gzip
    * If settings.DEBUG set, will gzip only if request is an ajax request
* This allows you to use django-debug-toolbar in DEBUG mode (if you gzip a response then the debug toolbar middleware won't run)

Example

```python

@allianceutils.views.decorators.gzip_page_ajax
def my_view(request: HttpRequest) -> httpResponse:
    data = {
        "message": "Hello World",
    }
    return django.http.JsonResponse(data)

```

#### method_cache

* Caches the results of a method on the object instance
* There is no thread synchronization so in some circumstances the method may be called multiple times if multiple threads share the object
* Only works for regular object methods with no arguments other than `self`.
    * Does not support `@classmethod` or `@staticmethod`
    * If you want more powerful caching behaviour then you can
      * use [`methodtools`](https://pypi.org/project/methodtools/)
      * wrap `cachetools` (examples [here](https://github.com/tkem/cachetools/issues/107#issuecomment-436274285))
* Similar to [`@cached_property`](https://docs.python.org/3/library/functools.html#functools.cached_property) except that it works on methods instead of properties
* Differs from [`@lru_cache()`](https://docs.python.org/3/library/functools.html#functools.lru_cache) in that
    * `lru_cache` uses a single cache for each decorated function
    * `lru_cache` will block garbage collection of values in the cache
    * A `cache_clear()` method is attached to the function but unlike `lru_cache` it is scoped to an object instance

Usage
```python
class MyViewSet(ViewSet):

    # ...

    @method_cache
    def get_object(self):
        return super().get_object()

obj = MyViewSet()
obj.get_object() is obj.get_object()
obj.get_object.cache_clear()
```

### Management

#### Commands

##### OptionalAppCommand

* A utility class that extends `django.core.management.base.BaseCommand` and adds optional argument(s) for django apps
* If app names are passed on the command line `handle_app_config()` will be called with the `AppConfig` for each app otherwise it will be called with every first-party app (as determined by `isort`)


Example:

```python
class Command(allianceutils.management.commands.base.OptionalAppCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--type', choices=('name', 'label'), default='name')

    def handle_app_config(self, app_config: AppConfig, **options):
        if options['type'] == 'name':
            print(f"Called with {app_config.name}")
        if options['type'] == 'label':
            print(f"Called with {app_config.label}")
```

##### print_logging

* Displays the current logging configuration in a hierarchical fashion
* Requires [`logging_tree`](https://pypi.python.org/pypi/logging_tree) to be installed

#### Checks

* Checks with no configuration are functions that can be passed directly to [register](https://docs.djangoproject.com/en/3.1/topics/checks/)
* Checks that expect parameters are classes that need to be instantiated

Setting up django hooks:

```python
from django.apps import AppConfig
from django.core.checks import register
from django.core.checks import Tags

from allianceutils.checks import check_admins
from allianceutils.checks import check_db_constraints
from allianceutils.checks import check_duplicated_middleware
from allianceutils.checks import CheckExplicitTableNames
from allianceutils.checks import check_git_hooks
from allianceutils.checks import CheckReversibleFieldNames
from allianceutils.checks import CheckUrlTrailingSlash

class MyAppConfig(AppConfig):
    # ...

    def ready(self):
        register(check=check_admins, tags=Tags.admin, deploy=True)
        register(check=check_db_constraints, tags=Tags.database)
        register(check=check_duplicated_middleware, tags=Tags.admin)
        register(check=CheckExplicitTableNames(), tags=Tags.models)
        register(check=check_git_hooks, tags=Tags.admin)
        register(check=CheckReversibleFieldNames(), tags=Tags.models)
        register(check=CheckUrlTrailingSlash(expect_trailing_slash=True), tags=Tags.url)
```

##### CheckUrlTrailingSlash

* Checks that your URLs are consistent with the `settings.APPEND_SLASH`
* Arguments:
    * `ignore_attrs` - skip checks on url patterns where an attribute of the pattern matches something in here (see example above)
        * Most relevant attributes of a `RegexURLResolver`:
            * `_regex` - string used for regex matching. Defaults to `[r'^$']`
            * `app_name` - app name (only works for `include()` patterns). Defaults to `['djdt']` (django debug toolbar)
            * `namespace` - pattern defines a namespace
            * `lookup_str` - string defining view to use. Defaults to `['django.views.static.serve']`
        * Note that if you skip a resolver it will also skip checks on everything inside that resolver
* Note: If using Django REST Framework's [`DefaultRouter`](http://www.django-rest-framework.org/api-guide/routers/#defaultrouter) then you need to turn off `include_format_suffixes`:

```python
router = routers.DefaultRouter(trailing_slash=True)
router.include_format_suffixes = False
router.register(r'myurl', MyViewSet)
urlpatterns += router.urls
```


##### check\_admins

* Checks that `settings.ADMINS` has been properly set in settings files.

##### check\_git\_hooks

* Checks that git hookshave been set up, one of:
  * `.git/hooks` directory has been symlinked to the project's `git-hooks`
  * [`husky`](https://github.com/typicode/husky) hooks have been installed
*

##### check\_db\_constraints

* Checks that all models that specify `db_constraints` in their Meta will generate unique constraint names when truncated by the database.

##### CheckExplicitTableNames

* Checks that all first-party models have `db_table` explicitly defined on their Meta class, and the table name is in lowercase
* Arguments:
    * `enforce_lowercase` - check that there are no uppercase characters in the table name
    * `ignore_labels` - if an app label (eg `silk`) or app_label + model labels (eg `silk.request`)
        matches something in `ignore_labels` then it will be ignored.
        * `allianceutils.checks.DEFAULT_TABLE_NAME_CHECK_IGNORE` contains a default list of apps/models to ignore
        * Can be either a `str` or a regex (anything that contains a `.match()` method)

##### CheckReversibleFieldNames

* Checks that all models have fields names that are reversible with `underscorize`/`camelize`/`camel_to_underscore`/`underscore_to_camel`
* Arguments:
    * `ignore_labels` - ignore these apps/models: see `CheckExplicitTableNames`

### Middleware

#### HttpAuthMiddleware

* Middleware to enable basic http auth to block unwanted traffic from search engines and random visitors
    * Intended to be used on dev / staging servers
    * Is not a full authorization system: is a single hardcoded username/password and should be used on top of a proper authorization system

* Setup
    * Add `allianceutils.middleware.HttpAuthMiddleware` to `MIDDLEWARE`.
    * Add `HTTP_AUTH_USERNAME` and `HTTP_AUTH_PASSWORD` to appropriate setting file, e.g. `settings/production_staging.py`
        * Remember that you shouldn't be hardcoding credentials in code: read content from env vars or file

#### CurrentRequestMiddleware

* Middleware to enable accessing the current request from anywhere
    * Assumes that `threading.local` is not shared between requests (an assumption also made by django internationalisation)

* Setup
    * Add `allianceutils.middleware.CurrentRequestMiddleware` to `MIDDLEWARE`.

* Usage

```python
from allianceutils.middleware import CurrentRequestMiddleware

# Will return `None` if request not available. This will be the case when called outside of a request, for example
# from a management command.
request = CurrentRequestMiddleware.get_request()
```

#### CurrentUserMiddleware

* **NOTE:** If using `CurrentRequestMiddleware` you can access the user from there, and you do not need this middleware.

* Middleware to enable accessing the currently logged-in user without a request object.
    * Assumes that `threading.local` is not shared between requests (an assumption also made by django internationalisation)

* Setup
    * Add `allianceutils.middleware.CurrentUserMiddleware` to `MIDDLEWARE`.

* Usage

```python
from allianceutils.middleware import CurrentUserMiddleware

user = CurrentUserMiddleware.get_user()
```

#### QueryCountMiddleware

* Warns if query count reaches a given threshold
    * Threshold can be changed by setting `settings.QUERY_COUNT_WARNING_THRESHOLD`

* Usage
    * Add `allianceutils.middleware.CurrentUserMiddleware` to `MIDDLEWARE`.
    * Uses the `warnings` module to raise a warning; by default this is suppressed by django
        * To ensure `QueryCountWarning` is never suppressed

```python
warnings.simplefilter('always', allianceutils.middleware.QueryCountWarning)
```

* To increase the query count limit for one request, you can call `QueryCountMiddleware.increase_threshold(request, increment)`
* To set the query count limit for one request you can call `QueryCountMiddleware.set_threshold(request, threshold)`
  * Rather than hardcode a new limit, `increase_threshold()` is generally preferable
  * This can be useful to disable checks entirely (pass `0` as the new limit)


```python
def my_view(request, *args, **kwargs):
    request.QUERY_COUNT_WARNING_THRESHOLD += 10
    ...

```


### Migrations

#### Run SQL function
* Wrapper to `RunSQL` that reads SQL from a file instead of inline in python
* The reason you would do this as an external file & function is so that squashed migrations don't become unwieldy (django will inline and strip whitespace in the SQL)

Usage:
```python
class Migration(migrations.Migration):
    # ...
    operations = [
        allianceutils.migrations.RunSQLFromFile('my_app', '0001_intial.sql'),
    ]
```

### Models

#### Utility functions / classes

##### combine_querysets_as_manager
* `allianceutils.models.combine_querysets_as_manager(Iterable[Queryset]) -> Manager`
* Replacement for django_permanent.managers.MultiPassThroughManager which no longer works in django 1.8
* Returns a new Manager instance that passes through calls to multiple underlying queryset_classes via inheritance

##### NoDeleteModel

* A model that blocks deletes in django
    * Can still be deleted with manual queries
* Read django docs about [manager inheritance](https://docs.djangoproject.com/en/stable/topics/db/managers/#custom-managers-and-model-inheritance)
    * If you wish add your own manager, you need to combine the querysets:

```python
class MyModel(NoDeleteModel):
        objects = combine_querysets_as_manager(NoDeleteQuerySet, MyQuerySet)
```

#### GenericUserProfile
Allows you to iterate over a `User` table and have it return a corresponding `Profile` record without generating extra queries

Minimal example:

```python
# ------------------------------------------------------------------
# base User model

# If you're using django auth instead of authtools, you can just use
# GenericUserProfileManager instead of having to make your own manager class
class UserManager(GenericUserProfileManagerMixin, authtools.models.UserManager):
    pass

class User(GenericUserProfile, authtools.models.AbstractEmailUser):
    objects = UserManager()
    profiles = UserManager(select_related_profiles=True)

    # these are the tables that should be select_related()/prefetch_related()
    # to minimise queries
    related_profile_tables = [
        'customerprofile',
        'adminprofile',
    ]

    # the default implementation will iterate through the related profile tables
    # and return the first profile it can find. If you have custom logic for
    # choosing the profile for a user then you can do that here
    #
    # You would normally not access this directly but instead use the`.profile`
    # property that caches the return value of `get_profile()` and works
    # correctly for both user and profile records
    def get_profile(self) -> Model:
        # custom logic
        if datetime.now() > datetime.date(2000,1,1):
            return self
        return super().get_profile()


# ------------------------------------------------------------------
# Custom user profiles
class CustomerProfile(User):
    customer_details = models.CharField(max_length=191)


class AdminProfile(User):
    admin_details = models.CharField(max_length=191)

# ------------------------------------------------------------------
# Usage:

# a list of User records
users = list(User.objects.all())

# a list of Profile records: 1 query
# If a user has no profile then you get the original User record back
profiles = list(User.profiles.all())

# we can explicitly perform the transform on the queryset
profiles = list(User.objects.select_related_profiles().all())

# joining to profile tables: 1 query
# This assumes that RetailLocation.company.manager is a FK ref to the user table
# The syntax is a bit different because we can't modify the query generation
# in an unrelated table
qs = RetailLocation.objects.all()
qs = User.objects.select_related_profiles(qs, 'company__manager')
location_managers = list((loc, loc.company.manager.profile) for loc in qs.all())
```

* There is also an authentication backend that will load profiles instead of just User records
* If the `User` model has no `get_profile()` method then this backend is equivalent to the built-in django `django.contrib.auth.backends.ModelBackend`

```python
# ------------------------------------------------------------------
# Profile authentication middleware
AUTH_USER_MODEL = 'my_site.User'
AUTHENTICATION_BACKENDS = [
    'allianceutils.auth.backends.ProfileModelBackend',
]


def my_view(request):
    # standard django AuthenticationMiddleware will call the authentication backend
    profile = request.user
    return HttpResponse('Current user is ' + profile.username)

```

* Limitations:
    * Profile iteration does not work with `.values()` or `.values_list()`

#### raise_validation_errors

* The `raise_validation_errors` context manager enables cleaner code for constructing validation
    * [Django documentation](https://docs.djangoproject.com/en/stable/ref/models/instances/#django.db.models.Model.clean) recommends raising a `ValidationError` when you encounter a problem
    * This creates a poor user experience if there are multiple errors: the user only sees the first error and has to resubmit a form multiple times to fix problems
* `raise_validation_errors` accepts an (optional) function to wrap
    * The context manager returns a `ValidationError` subclass with an `add_error` function that follows the same rules as `django.forms.forms.BaseForm.add_error`
    * If the wrapped function raises a `ValidationError` then this will be merged into the `ValidationError` returned by the context manager
    * If the wrapped function raises any other exception then this will not be intercepted and the context block will not be executed
    * At the end of a block,
        * If code in the context block raised an exception (including a `ValidationError`) then this will not be caught
        * If `ValidationError` the context manager returned has any errors (either from `ve.add_error()` or from the wrapped function) then this will be raised

```python
    def clean(self):
        with allianceutils.models.raise_validation_errors(super().clean) as ve:
            if some_condition:
                ve.add_error(None, 'model error message')
            if other_condition:
                ve.add_error('fieldname', 'field-specific error message')
            if other_condition:
                ve.add_error(None, {
                    'fieldname1': field-specific error message',
                    'fieldname2': field-specific error message',
                })
            if something_bad:
                raise RuntimeError('Oh no!')

            # at the end of the context, ve will be raised if it contains any errors
            #   - unless an exception was raised in the block (RuntimeError example above) in which case
            #     the raised exception will take precedence
```

* Sometimes you already have functions that may raise a `ValidationError` and `add_error()` will not help
    * The `capture_validation_error()` context manager solves this problem
    * Note that due to the way context managers work, each potential `ValidationError` needs its own with `capture_validation_error` context

```python
    def clean(self):
        with allianceutils.models.raise_validation_errors() as ve:
             with ve.capture_validation_error():
                 self.func1()
             with ve.capture_validation_error():
                 self.func2()
             with ve.capture_validation_error():
                 raise ValidationError('bad things')
            # all raised ValidationErrors will be collected, merged and raised at the end of this block
```

### Rules

* Utility functions that return predicates for use with [django-rules](https://github.com/dfunckt/django-rules)

```python
from allianceutils.rules import has_any_perms, has_perms, has_perm

# requires at least 1 listed permission
rules.add_perm('northwind.publish_book', has_any_perms('northwind.is_book_author', 'northwind.is_book_editor'))

# requires listed permission
rules.add_perm('northwind.unpublish_book', has_perm('northwind.is_book_editor'))

# requires all listed permissions
rules.add_perm('northwind.sublicense_book', has_perms('northwind.is_book_editor', 'northwind.can_sign_contracts'))

```

### Serializers

#### JSON Ordered

* A version of django's core json serializer that outputs field in sorted order
* The built-in one uses a standard `dict` with completely unpredictable order which causes json diffs to show spurious changes

* Setup
    * Add to `SERIALIZATION_MODULES` in your settings
    * This will allow you to do fixture dumps with `--format json_ordered`
    * Note that django treats this as the file extension to use

```python
SERIALIZATION_MODULES = {
    'json_ordered': 'allianceutils.serializers.json_ordered',
}
```

### Template

##### resolve

* Resolves different types of kwarg values consistently.
  * If value is a NodeList then it is rendered
  * If value is a FilterExpression then it is resolved
  * If value is a dict then each element is resolved if it is a FilterExpression, or else returned as is
  * Otherwise value is returned as is


* Example Usage
```python
    def resolved_kwargs(self, context: Context):
        pk = resolve(self.pk, context)
        model = resolve(self.model_name, context)
        object = resolve(self.object, context)
```

##### token_kwargs

* Re-implements the `token_kwargs` function from the Django base template library. This allows expanding the range of possible keywords to include '-' for aria attributes (e.g. `aria-label="My Label"`), and ':' for namespaced attributes (e.g. `xlink:href="foo"`). Used internally in [parse_tag_arguments](#parse_tag_arguments) - see that section for usage

##### parse_tag_arguments

* Implements a stripped-down version of `django.template.library.parse_bits()` to parse tokens passed to tags in Django templates.
  * Takes the parser to process the tag, the token passed to the tag, and the kwarg `supports_as`
  * Returns a tuple of `(args: list, kwargs: dict, target_var: str)`:
    * args: a list of args as FilterExpressions
    * kwargs: a dict of kwargs
    * target_var: if `supports_as` is `True` and `as <variable>` is specified, returns the string reference for the tag. Otherwise returns `None`


* Example Usage

```python
class StylesheetNode(template.Node, BundlerAsset):
    def __init__(self, filename: Path, origin: Origin | None, attrs=None, target_var=None):
        self.filename = filename
        self.attrs = attrs
        self.target_var = target_var
        super().__init__(origin or Origin(UNKNOWN_SOURCE))

    def render(self, context: Context):
        if self.target_var:
            context[self.target_var] = get_classes(self.filename)

@register.tag("stylesheet")
def stylesheet(parser: template.base.Parser, token: template.base.Token):
    args, kwargs, target_var = parse_tag_arguments(parser, token, supports_as=True)
    filename = args[0]
    return StylesheetNode(filename, parser.origin, kwargs, target_var=target_var)
```

```html
    {% stylesheet "./theme.css" as styles %}

    <div class="{{ styles.section }}">
        <h1 class="{{ styles.heading }}">My View</h1>
        ...
    </div>
```

##### build_html_attrs

* Takes a dict of HTML tag attributes and transforms values into escaped strings suitable for use as HTML tag attributes. Can also pass a list of `prohibited_attrs` to prevent passing attributes which should not be passed to template tags.

* Example Usage
```python
from django.utils.html import format_html
...
class LinkNode(template.Node):
    def __init__(
        self,
        *,
        href: FilterExpression | str | None = None,
        **extra_kwargs,
    ) -> None:
        self.href = href

    ...

    def render(self, context: Context) -> SafeString:
        href = resolve(self.href, context)
        html_kwargs = { "href": href }
        html_attrs = build_html_attrs(html_kwargs)
        return format_html(
            "<a {}>{}</a>",
            html_attrs,
        )
```

```html
    {% link "/home" %}
```

##### is_static_expression

* Checks if a given FilterExpression is static using the same method as Django's `resolve` implementation for the `Variable` class

* Example Usage
```python
def validate_tag(parser, token):
    tag_name = token.split_contents()[0]
    args, _, _ = parse_tag_arguments(parser, token)

    for arg in args:
        if not is_static_expression(arg):
            raise TemplateSyntaxError(
                f"{tag_name} must be passed static strings for its arguments (encountered variable '{arg.var}')"
            )
```

### Template Tags

#### render_entry_point

* Replaces old usage of [django-webpack-loader](https://github.com/ezhome/django-webpack-loader)
   * At time of writing django-webpack-loader does not have a stable release that [works with webpack 4](https://github.com/owais/django-webpack-loader/issues/218)
   * Worked at bundle level rather than entry point. See below for how we embed tags based on entry point.
* Reads JSON files generated by [EntryPointBundleTracker](https://gitlab.internal.alliancesoftware.com.au/alliance/webpack-dev-utils/) and embeds the required bundles in the page
   * Will output tags for all resources of the specified type. eg. Given JSON structure of:
   ```json
    {
      "status": "done",
      "entrypoints": {
        "admin": [
          {
            "name": "runtime.bundle.js",
            "contentHash": "e2b781da02d36dad3aff"
          },
          {
            "name": "common.bundle.js",
            "contentHash": "639269b921c8cf869c5f"
          },
          {
            "name": "common.bundle.css",
            "contentHash": "d60a0fa36613ea58a23d"
          },
          {
            "name": "admin.bundle.js",
            "contentHash": "c78fb252d4e00207afef"
          }
        ]
      },
      "publicPath": "/assets/"
    }
   ```

   Output for `{% render_entry_point 'admin' 'js' %}`:

   ```html
   <script type="text/javascript" src="/assets/runtime.bundle.js?e2b781da02d36dad3aff"></script>
   <script type="text/javascript" src="/assets/common.bundle.js?639269b921c8cf869c5f"></script>
   <script type="text/javascript" src="/assets/admin.bundle.js?c78fb252d4e00207afef"></script>
   ```

   Output for `{% render_entry_point 'admin' 'css' %}`:

   ```html
   <link type="text/css" href="/assets/common.bundle.css?d60a0fa36613ea58a23d" rel="stylesheet" />
   ```
* As an entry point maps to a single HTML file it's expected you would only use this tag for a single entry point on a page but generally would call it for both `js` and `css`
* Arguments
  * `entry_point_name` - Name of the entry point. This should match one of the entries to 'entry' in the webpack config.
  * `resource_type` - The resource type to embed; either `js` or `css`.
* Optional Arguments
  * `attrs` - String representing extra attributes to pass to the HTML tag
  * `config='DEFAULT'` - String index into the settings `WEBPACK_LOADER` dict. Defaults to 'DEFAULT'.
* Config
  * Configuration can be specified via the `WEBPACK_LOADER` setting. This is a dict indexed by the config name (defaults to 'DEFAULT')
  * Options
    * `STATS_FILE` - the path to the stats file to read
    * `INCLUDE_QUERY_HASH` - whether to include the content hash in the query string. Defaults to `true`.
    * `BASE_URL` - a URL to prepend to all chunks when rendered. This can be used when files are stored on a different host (eg. CDN).

* Example Usage

```html
{% load alliance_webpack %}
<html>
<head>
  {% render_entry_point 'app' 'css' %}
</head>
<body>

  ...

  {% if DEBUG %}
    {# See https://reactjs.org/docs/cross-origin-errors.html #}
    {% render_entry_point entry_point 'js' attrs="crossorigin" %}
  {% else %}
    {% render_entry_point entry_point 'js' %}
  {% endif %}
</body>
</html>
```

#### default_value

* Sets default value(s) on the context in a template
* This is useful because some built-in django templates raise warnings about unset variables (eg `is_popup` in the django admin template)
* Note that some tags (eg `with`) save & restore the context state; if done inside such a template tag `default_value` will not persist when the state is restored

```html
{% load default_value %}
{{ default_value myvar1=99 myvar2=myvar1|upper }}
{{ myvar1 }} {{ myvar2 }}
```

### Tests

##### suppress_silk

* Decorator to disable silk SQL query logging.
* This is needed for tests that use `assertNumQueries()` since otherwise the query count may include silk's `EXPLAIN`

* Example Usage

```python
    @suppress_silk()
    def test_lookup_object(self):
        """Test that a query is run if object is not provided in template"""
        user = self.get_privileged_user()
        viewname = self.VIEW_KWARGS
        view_kwargs = {"pk": user.pk}

        request = HttpRequest()

        # Without suppress_silk, an EXPLAIN query will be added
        with self.assertNumQueries(1):
            tpl = Template('{% load link %}{% link "' + viewname + '" pk=pk %}foo{% endlink %}')
            tpl.render(Context({"request": request, "user": user, **view_kwargs}))
```

##### logging_filter

* Decorator to disable logging for specified log names
* This is useful because using `override_settings(LOGGING=...)` triggers an update to the python logging settings

* Example Usage
```python
    @logging_filter(["django.request"])
    def test_django_validation_errors(self):
        url = reverse("django-validation-test-url")
        for key, expect in EXPECTED_RESPONSES.items():
            with self.subTest(key=key):
                response = self.client.post(url, data={"error_key": key}, format="json")
                self.assertEqual(400, response.status_code)
                self.assertEqual(expect, response.json())
```

##### warning_filter

* Apply a `warning.simplefilter()` for the specified warnings

* Example Usage
```python
    @warning_filter("ignore", category=DeprecationWarning)
    def test_relying_on_deprecated_feature(self):
        instance = MyModel.objects.filter(deprecated_filter=True)
        assertIsInstance(instance, MyModel)
```

### Util

#### add_autoreload_extra_files

* Adds files to the autoreloader watch list
    * Works with both the built-in [`runserver`](https://docs.djangoproject.com/en/stable/ref/django-admin/#runserver)
      and [`runserver_plus`](https://django-extensions.readthedocs.io/en/latest/runserver_plus.html) from `django-extensions`
    * If `DEBUG` is not enabled then this will do nothing
    * This should be called from inside the
      [`ready()`](https://docs.djangoproject.com/en/stable/ref/applications/#django.apps.AppConfig.ready) method of
      an [`AppConfig`](https://docs.djangoproject.com/en/stable/ref/applications/#configuring-applications)

```python
class MyAppConfig(AppConfig):
    def ready(self):
        extra_files = [
          "/data/file.csv",
        ]
        add_autoreload_extra_files(extra_files)
```

#### camelize

* Better version of [djangorestframework-camel-case](https://github.com/vbabiy/djangorestframework-camel-case)
    * DRF-CC camel cases every single key in the data tree.
* These functions allow you to indicate that certain keys are data, not field names


```python
tree = {
    "first_name": "Mary",
    "last_name": "Smith",
    "servers": {
        "server_west.mycompany.com": {
            'user_accounts': {
                'mary_smith': {
                    'home_dir': '/home/mary_smith',
                },
            },
        },
    },
}
# the keys at tree['servers'] and tree['servers']['serve_west.mycompany.com']['user_accounts'] will not be camel cased
output_tree = allianceutils.util.camelize(tree, ignore=['servers', 'servers.*.user_accounts'])
output_tree == {
    "firstName": "Mary",
    "lastName": "Smith",
    "servers": {
        "server_west.mycompany.com": {
            'userAccounts': {
                'mary_smith': {
                    'home_dir': '/home/mary_smith',
                },
            },
        },
    },
}

```

* `allianceutils.util.camelize(data, ignores)` - underscore case => camel case a json tree of data
* `allianceutils.util.underscorize(data, ignores)` - camel case => underscore case a json tree of data
* `allianceutils.util.camel_to_underscore(str)` - underscore case => camel case a string
* `allianceutils.util.underscore_to_camel(str)` - camel case => underscore case a string
* It is assumed that words will not begin with numbers:
    * `zoo_foo99_bar` is okay
    * `zoo_foo_99bar` will result in an irreversible transformation (`zooFoo99bar` => `zoo_foo99_bar`)

#### get_firstparty_apps

`util.get_firstparty_apps` can be used to retrieve app_configs considered to be first party, ie, all that does not come from a third party package.
This is beneficial when you want to write your own checks by excluding things you dont really care - a sample usage can be found inside 'checks.py', or
used as such:

```python

from allianceutils.util import get_firstparty_apps

app_configs = get_firstparty_apps()
models_to_be_checked = {}

for app_config in app_configs:
    models_to_be_checked.update({
        model._meta.label: model
        for model
        in app_config.get_models()
    })
```

#### python_to_django_date_format

* Converts a python [strftime/strptime](https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior) datetime format string into a [django template/PHP](https://docs.djangoproject.com/en/stable/ref/templates/builtins/#std:templatefilter-date) date format string
* Codes with no equivalent will be dropped

Example:
```python
allianceutils.util.date.python_to_django_date_format("%Y%m%d %H%M%S")
# returns "Ymd His"
```

#### retry_fn

* Repeatedly (up to a hard limit) call specified function while it raises specified exception types or until it returns

```python
from allianceutils.util import retry_fn

# Generate next number in sequence for a model
# Number here has unique constraint resulting in IntegrityError being thrown
# whenever a duplicate is added. can be useful for working around mysql's lack
# of sequences
def generate_number():
    qs = MyModel.objects.aggregate(last_number=Max(F('card_number')))
    next_number = (qs.get('last_card_number') or 0) + 1
    self.card_number = card_number
    super().save(*args, **kwargs)
retry_fn(generate_number, (IntegrityError, ), 10)
```

## Experimental

* These are experimental and may change without notice
    * `document_reverse_accessors` management command

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## Development

* To create a clean local environment
  * `python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip`
  * `poetry install --no-root --sync --only=main --extras=""`
  * Note that due to [a poetry bug](https://github.com/python-poetry/poetry/issues/7364) extras are currently not removed
  * This will install the latest django version; if you want to test a specific django version you need to `pip install` it manually
* Dev dependencies
  * `poetry install --no-root --sync --with=dev --extras "extras mysql postgres"`

### Release Process

#### Poetry Config
* Add test repository
    * `poetry config repositories.testpypi https://test.pypi.org/legacy/`
    * Generate an account API token at https://test.pypi.org/manage/account/token/
    * `poetry config pypi-token.testpypi ${TOKEN}`
        * On macs this will be stored in the `login` keychain at `poetry-repository-testpypi`
* Main pypi repository
    * Generate an account API token at https://pypi.org/manage/account/token/
    * `poetry config pypi-token.pypi ${TOKEN}`
        * On macs this will be stored in the `login` keychain at `poetry-repository-pypi`

#### Publishing a New Release
    * Update CHANGELOG.md with details of changes and new version
    * Run `bin/build.py`. This will extract version from CHANGELOG.md, bump version in `pyproject.toml` and generate a build for publishing
    * Commit version bumps
    * Tag with new version and update the version branch:
        * `ver=$( poetry version --short ) && echo "Version: $ver"`
        * `git tag v/$ver`
        * `git push --tags`
    * To publish to test.pypi.org
        * `poetry publish --repository testpypi`
    * To publish to pypi.org
        * `poetry publish`


### Testing
* To run test cases
  * The django settings module is `test_allianceutils/settings.py`
    * The following env vars are optional but you may want to set them if the default don't match your local setup:
      * `DB_NAME`
      * `DB_HOST`
      * `DB_PORT`
      * `DB_USER`
      * `DB_PASSWORD`
* [tox](https://tox.wiki/en/latest/)
  * used to run tests against different django/python/database versions
  * `tox` to run all tests. Will require that you have a postgres & mysql server running.
    * `tox -f django42` will run the subset of tests that cover django 4.2. Check `tox.ini` for the list of tested environments.
* When you push to github a [github Actions](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python) workflow will be triggered (see `.github/workflows/django.yml`)
