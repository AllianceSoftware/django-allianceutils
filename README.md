# Alliance Utils

![CI Tests](https://github.com/AllianceSoftware/django-allianceutils/workflows/Django%20CI/badge.svg)

A collection of utilities for django projects from [Alliance Software](https://www.alliancesoftware.com.au/).

* [Installation](#installation)
* [Usage](#usage)
    * [API](#api)
    * [Auth](#auth)
    * [Decorators](#decorators)
    * [Filters](#filters)
    * [Management](#management)
        * [Commands](#commands)
        * [Checks](#checks)
    * [Middleware](#middleware)
    * [Migrations](#migrations)
    * [Models](#models)
    * [Rules](#rules)
    * [Serializers](#serializers)
    * [Template Tags](#template-tags)
    * [Util](#util)
* [Changelog](#changelog)

## Installation

`pip install django-allianceutils`

## System Requirements

* Tested with django 2.2 and 3.2
  * Pull requests accepted for other versions, but at minimum we test against current LTS versions
* Python >=3.6 (no python 3.5 support)

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

```py
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
```
class MyViewSet(GenericDjangoViewsetPermissions, viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MySerializer
```
* `GenericDjangoViewsetPermissions.default_actions_to_perms_map` defines the default set of permissions. These can be extended or overridden using `actions_to_perms_map`:
```
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
    * ~`allianceutils.auth.backends.ProfileModelBackend`~ - convenience class combined with case insensitive username & default django permissions backend
        * this depended on [`authtools`](https://django-authtools.readthedocs.io/en/latest/) which appears to have been
          abandoned and does not work with django >= 3.
          If using django 3 then we recommended that you create your own backend in your app:
          ```python
            class ProfileModelBackend(ProfileModelBackendMixin, MinimalModelBackend):
                # you'll need to implement case insensitivity either here or in the User Model  
                pass
          ```

### Decorators

#### gzip_page_ajax

* Smarter version of django's [gzip_page](https://docs.djangoproject.com/en/stable/topics/http/decorators/#django.views.decorators.gzip.gzip_page):
    * If settings.DEBUG not set, will always gzip
    * If settings.DEBUG set, will gzip only if request is an ajax request
* This allows you to use django-debug-toolbar in DEBUG mode (if you gzip a response then the debug toolbar middleware won't run)

Example

```

@allianceutils.views.decorators.gzip_page_ajax
def my_view(request: HttpRequest) -> httpResponse:
    data = {
        "message": "Hello World",
    }
    return django.http.JsonResponse(data) 

```

#### method_cache

* Caches the results of a method on the object instance
* Only works for regular object methods with no arguments other than `self`.
    * Does not support `@classmethod` or `@staticmethod`
    * If you want more powerful caching behaviour then you can wrap `cachetools` (examples [here](https://github.com/tkem/cachetools/issues/107))
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

### Filters

#### MultipleFieldCharFilter

Search for a string across multiple fields. Requires `django_filters`.

* Usage 

```python
from allianceutils.filters import MultipleFieldCharFilter

# ...
# In your filter set (see django_filters for documentation)
customer = MultipleFieldCharFilter(names=('customer__first_name', 'customer__last_name'), lookup_expr='icontains')
```

### Management

#### Commands

##### OptionalAppCommand

* A utility class that extends `django.core.management.base.BaseCommand` and adds optional argument(s) for django apps
* If app names are passed on the command line `handle_app_config()` will be called with the `AppConfig` for each app otherwise it will be called with every first-party app (as determined by `isort`)


Example:

```
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
from allianceutils.checks import CheckExplicitTableNames
from allianceutils.checks import check_git_hooks
from allianceutils.checks import CheckReversibleFieldNames
from allianceutils.checks import CheckUrlTrailingSlash

class MyAppConfig(AppConfig):
    # ...

    def ready(self):
        register(check=check_admins, tags=Tags.admin, deploy=True)
        register(check=check_db_constraints, tags=Tags.database)
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

```
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

#### CurrentUserMiddleware

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

* To increase the query count limit for a given request, you can increase `request.QUERY_COUNT_WARNING_THRESHOLD`
    * Rather than hardcode a new limit, you should increment the existing value
    * If `request.QUERY_COUNT_WARNING_THRESHOLD` is falsy then checks are disabled for this request 

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

    def natural_key(self):
        return (self.email,)
        
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

```
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

```
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

```
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
    * Tag with new version and update the version branch:
        * `ver=$( poetry version --short ) && echo "Version: $ver"`
        * `git tag v/$ver`
        * `git push --tags`
    * To publish to test.pypi.org
        * `poetry publish --repository testpypi`
    * To publish to pypi.org
        * `poetry publish`


