# Alliance Utils

A collection of utilities for django projects.

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
    * [Serializers](#serializers)
    * [Storage](#storage)
    * [Template Tags](#template-tags)
    * [Util](#util)
    * [Views](#views)
* [Changelog](#changelog)

## Installation

`pip install -e git+git@gitlab.internal.alliancesoftware.com.au:alliance/alliance-django-utils.git@master#egg=allianceutils`

## Usage

### API

#### CacheObjectMixin

**Status: No unit tests**

Caches the result of `get_object()` in the request
* TODO: Why cache this on `request` and not on `self`?
    * If you are customising `get_object()`, `django.utils.functional.cached_property` is probably simpler 

```python
class MyViewSet(allianceutils.api.mixins.CacheObjectMixin, GenericViewSet):
    # ...
```  

#### Permissions

##### SimpleDjangoObjectPermissions

**Status: No unit tests**

Permission class for Django Rest Framework that adds support for object level permissions.

Differs from just using DjangoObjectPermissions because it
* does not require a queryset
* uses a single permission for all request methods

Notes
* As per [DRF documentation](http://www.django-rest-framework.org/api-guide/permissions/#object-level-permissions): get_object() is only required if you want to implement object-level permissions
* **WARNING** If you override `get_object()` then you need to *manually* invoke `self.check_object_permissions(self.request, obj)`

Setup
* To apply to all classes in django rest framework:

```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        # default to requiring authentication & a role
        # you can override this by setting the permission_classes to AllowAny in the view
        'rest_framework.permissions.IsAuthenticated',
        'allianceutils.api.permissions.SimpleDjangoObjectPermissions',
    ),
}
```

* To apply to one particular view, override `permission_required`
```python
class MyAPIView(PermissionRequiredAPIMixin, APIView):
        permission_required = 'my_module.my_permission'

        # You do not have to override get_object() but if you do you must explicitly call check_object_permissions() 
        def get_object(self):
            obj = get_object_or_404(self.get_queryset())
            self.check_object_permissions(self.request, obj)
            return obj
```

If you have no object level permissions (eg. from rules) then it will just do a static permission check.


##### GenericDjangoViewsetPermissions

**Status: No unit tests**

### Auth

FIXME

### Decorators

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

##### mysqlquickdump

* Command to quickly dump a mysql database
    * Significantly faster than django fixtures
* Can be useful for saving & restoring the state of the database in test cases
    * Not intended to be used on production servers
* Expects that DB structure will not change
* See `./manage.py mysqlquickdump --help` for usage details

##### mysqlquickload

* Load a database dumped with `mysqlquickdump`
* See `./manage.py mysqlquickload --help` for usage details

##### print_logging

* Displays the current logging configuration in a hierarchical fashion
* Requires [`logging_tree`](https://pypi.python.org/pypi/logging_tree) to be installed

#### Checks

##### check_url_trailing_slash

* Checks that your URLs are consistent with the `settings.APPEND_SLASH` using a [django system check](https://docs.djangoproject.com/en/dev/ref/checks/)
* In your [app config](https://docs.djangoproject.com/en/1.11/ref/applications/#for-application-authors) 

```python
from django.apps import AppConfig
from django.core.checks import register
from django.core.checks import Tags

from allianceutils.checks import check_url_trailing_slash

class MyAppConfig(AppConfig):
    # ...

    def ready(self):
        # trigger checks to register
        check = check_url_trailing_slash(expect_trailing_slash=True)
        register(check=check, tags=Tags.url)
```

* Optional arguments to `check_url_trailing_slash`
    * `ignore_attrs` - skip checks on url patterns where an attribute of the pattern matches something in here (see example above)
        * Most relevant attributes of a `RegexURLResolver`:
            * `_regex` - string used for regex matching. Defaults to `[r'^$']`
            * `app_name` - app name (only works for `include()` patterns). Defaults to `['djdt']` (django debug toolbar)
            * `namespace` - pattern defines a namespace
            * `lookup_str` - string defining view to use. Defaults to `['django.views.static.serve']`
        * Note that if you skip a resolver it will also skip checks on everything inside that resolver
* If using Django REST Framework's [`DefaultRouter`](http://www.django-rest-framework.org/api-guide/routers/#defaultrouter) then you need to turn off `include_format_suffixes`:

```
router = routers.DefaultRouter(trailing_slash=True)
router.include_format_suffixes = False
router.register(r'myurl', MyViewSet)
urlpatterns += router.urls
```


##### check\_admins

* Checks that `settings.ADMINS` has been properly set in staging and production settings files.

##### check\_git\_hooks

* Checks that the `.git/hooks` directory has been sym-linked to the projects' `git-hooks` directory.

##### check\_db\_constraints

* Checks that all models that specify `db_constraints` in their Meta will generate unique constraint names when truncated by the database.


### Middleware

#### CurrentUserMiddleware

* Middleware to enable accessing the currently logged-in user without a request object.
    * Properly handles multithreaded python by keeping track of the current user in a `dict` of `{'threadId': User}` 

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

FIXME

### Models

#### Utility functions / classes

##### Authentication functions
* `add_group_permissions(group_id, codenames)`
    * Add permissions to a given group (permissions must already exist)
* `get_users_with_permission(permission)`
    * Single-permission shorthand for `get_users_with_permissions` 
* `get_users_with_permissions(permissions)`
    * Gets all users with any of the specified static permissions

##### combine_querysets_as_manager
* Replacement for django_permanent.managers.MultiPassThroughManager which no longer works in django 1.8
* Returns a new Manager instance that passes through calls to multiple underlying queryset_classes via inheritance 

##### NoDeleteModel

* A model that blocks deletes in django
    * Can still be deleted with manual queries
* Read django docs about [manager inheritance](https://docs.djangoproject.com/en/1.11/topics/db/managers/#custom-managers-and-model-inheritance)
    * If you wish add your own manager, you need to combine the querysets:

```python
class MyModel(NoDeleteModel):
        objects = combine_querysets_as_manager(NoDeleteQuerySet, MyQuerySet)
```  

#### GenericUserProfile
Allows you to iterate over a `User` table and have it return the corresponding `Profile` records without generating extra queries

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
    * [Django documentation](https://docs.djangoproject.com/en/dev/ref/models/instances/#django.db.models.Model.clean) recommends raising a `ValidationError` when you encounter a problem
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

### Serializers

#### JSON Ordered

* A version of django's core json serializer that outputs field in sorted order
* The built-in one uses a standard `dict` with completely unpredictable order which makes fixture diffs often contain field ordering changes

* Setup
    * Add to `SERIALIZATION_MODULES` in your settings
    * This will allow you to do fixture dumps with `--format json_ordered`
    * Note that django treats this as the file extension to use

```python
SERIALIZATION_MODULES = {
    'json_ordered': 'allianceutils.serializers.json_ordered',
}
```

#### JSON ORM Inheritance Fix

* Django does not properly handle (de)serialise models with natural keys where the PK is a FK
    * This shows up particularly with multi-table inheritance and the user profile pattern
    * https://code.djangoproject.com/ticket/24607
        * Patch was accepted into 1.11 but then removed
        * We are willing to deal with potentially spurious migrations in order to have fixtures work
* We need to replace not only the serializer but also the deserializer
* Note that child models will not inherit the parent `Manager` if the parent is not `abstract`; you need to define a `Manager` that has a `get_by_natural_key()` in each descendant model if you use FK references to the descendant model. 

```python
SERIALIZATION_MODULES = {
    'json': 'allianceutils.serializers.json_orminheritancefix',
}
```

### Storage

* Requires `django-storages` and `boto3` to be installed

* Use the below if you are using S3 for file storage and want to prefix media and / or static files - otherwise they will all be dumped unprefixed in the bucket.

* Configure S3 for use with S3 Boto3

```python
AWS_ACCESS_KEY_ID = 'ACCESS_KEY'
AWS_STORAGE_BUCKET_NAME = 'bucket-name'
AWS_DEFAULT_REGION = 'ap-southeast-2'
AWS_DEFAULT_ACL = None
```

#### StaticStorage

* An extension to S3Boto3Storage that specifies a prefix for static files.
* Allows you to put static files and media files in S3 without worrying about clobbering each other.
* Note that if using on Heroku this doesn't play nice with pipelines so you probably don't want to use it
* Configuration

```python
STATICFILES_STORAGE = 'allianceutils.storage.StaticStorage'
STATICFILES_LOCATION="static"

STATIC_URL = "https://%s.s3.amazonaws.com/%s/" % (AWS_STORAGE_BUCKET_NAME, STATICFILES_LOCATION)
```

#### MediaStorage

* An extension to S3Boto3Storage that specifies a prefix for static files.
* Allows you to put static files and media files in S3 without worrying about clobbering each other.

Configuration:

```python
DEFAULT_FILE_STORAGE = 'allianceutils.storage.MediaStorage'
MEDIAFILES_LOCATION="media"

MEDIA_URL = "https://%s.s3.amazonaws.com/%s/" % (AWS_STORAGE_BUCKET_NAME, MEDIAFILES_LOCATION)
```

### Template Tags

#### render_entry_point

* Replaces old usage of [django-webpack-loader](https://github.com/ezhome/django-webpack-loader)
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

#### python_to_django_date_format

Converts a python [strftime/strptime](https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior) datetime format string into a []django template/PHP](https://docs.djangoproject.com/en/dev/ref/templates/builtins/#std:templatefilter-date) date format string

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

### Views 

#### JSONExceptionAPIView

FIXME


## Changelog

* Note: `setup.py` reads the highest version number from this section, so use versioning compatible with setuptools
* 0.5
    * 0.6.dev
        * Adds warning message when webpack's compiling / takes too long to compile
        * Removed autodumpdata and its related checks
        * Fix `GenericUserProfileQueryset` values() and values_list() incorrectly reject all args
        * CurrentUserMiddleware now supports the post-django-1.11 MIDDLEWARE
    * 0.5.0
        * Breaking Changes    
            * drop support for python 3.4, 3.5
            * `alliance_bundle` removed
            * `TimestampWebpackLoader`, `ContentHashWebpackLoader` removed
        * django 2.1 support
        * remove `unipath` dependency
        * Added `checks.make_check_autodumpdata`, simplified mechanism to ignore missing autodumpdata warnings
        * Added `checks.check_git_hooks`, ensure .git/hooks directory sym-linked to git-hooks
        * Added `checks.check_admins`, ensure settings.ADMINS has been set for staging/production
        * Added `checks.check_db_constraints`, ensure db_constraints are unique when truncated
        * Add `render_entry_point` tag
        * Fix `QueryCountMiddleware` reporting incorrect query counts when run in multithreaded server 
* 0.4
    * 0.4.2
        * `GenericUserProfileManagerMixin` rewritten; interface has changed, now works correctly
    * 0.4.1
        * Breaking Changes
           * Specify behaviour of numbers in underscore/camel case conversion (was undefined before) 
        * Add `raise_validation_errors`
    * 0.4.0
        * Breaking Changes
           * The interface for `get_autodump_labels` has changed
        * Add `checks.check_autodumpdata` 
* 0.3
    * 0.3.4
        * Add `camel_case`
        * Add `print_logging` management command
        * Fix `GenericUserProfile` raising the wrong model exceptions; removed `GenericUserProfileManager.use_proxy_model` 
        * Mark `script_json` for future removal
    * 0.3.3
        * Add `default_value`
        * Add tests
            * For `alliance_bundle` 
            * For `ContentHashWebpackLoader` & `TimestampWebpackLoader`
    * 0.3.2
        * Fix `check_url_trailing_slash` failing with `admin.site.urls`
    * 0.3.1
        * Fix install failure with setuptools<20.3  
    * 0.3.0
        * Breaking Changes
            * Dropped support for python <3.4
            * Dropped support for django <1.11
        * Add `GenericUserProfile`
        * Add `python_to_django_date_format`
        * Add `check_url_trailing_slash`
        * Add `QueryCountMiddleware`
        * Test against python 3.4, 3.5, 3.6
* 0.2
    * 0.2.0
        * Breaking Changes
            * The interface for `get_autodump_labels` has changed 
        * Add autodumpdata SQL output format
        * Add `mysqlquickdump` options `--model` and `--explicit` 
        * Update to work with webpack_loader 0.5
* 0.1
    * 0.1.6
        * Update `json_orminheritancefix` to work with django 1.11 
    * 0.1.5
        * Fix missing import if using autodumpdata automatically calculated filenames
        * autodumpdata now creates missing fixture directory automatically
    * 0.1.4
        * Fix bad versioning in previous release
    * 0.1.3
        * Add autodumpdata test cases
        * Add autodumpdata `--stdout`, `--output` options
        * Fix autodumpdata failing if `settings.SERIALIZATION_MODULES` not defined
    * 0.1.2
        * Add test cases, documentation
    * 0.1.1
        * Add `StaticStorage`, `MediaStorage`
    * 0.1.0
        * Initial release
