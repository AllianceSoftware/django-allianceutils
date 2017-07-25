# Alliance Utils

A collection of utilities for django projects.

* [Installation](#installation)
* [Usage](#usage)
    * [API](#api)
    * [Auth](#auth)
    * [Commands](#commands)
    * [Decorators](#decorators)
    * [Filters](#filters)
    * [Management](#management)
    * [Middleware](#middleware)
    * [Migrations](#migrations)
    * [Models](#models)
    * [Serializers](#serializers)
    * [Storage](#storage)
    * [Template Tags](#template-tags)
    * [Views](#views)
    * [Webpack](#webpack)
* [Changelog](#changelog)

## Installation

`pip install -e git+git@gitlab.internal.alliancesoftware.com.au:alliance/alliance-django-utils.git@master#egg=allianceutils`

## Usage

### API

FIXME
#### Permissions

##### SimpleDjangoObjectPermissions

Permission class for Django Rest Framework that adds support for object level permissions.

* Setup
    * Add to `REST_FRAMEWORK` `DEFAULT_PERMISSION_CLASSES` in your settings

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

* Usage 

In a view set `permission_required` to the static permission required:

```
ass AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    queryset = Account.objects.all()

    permission_required = 'password_manager.view_account'
```

If you have no object level permissions (eg. from rules) then it will just do a static
permission check.


### Auth

FIXME

### Commands

#### autodumpdata

* Designed to more conveniently allow dumping of data from different models into different fixtures
* Strongly advised to also use the [Serializers](#serializers)

* For each model, add a list of fixtures that this model should be part of in the `fixures_autodump` list
    * The following will dump the Customer model as part of the `customers` and `test` fixtures

```python
class Customer(models.Model):
    fixtures_autodump = ['customers', 'test']
```

* If `autodumpdata` is invoked without a fixture, it defaults to `dev`
* This is particularly useful for dumping django group permissions (which you typically want to send to a live server) separately from test data
* To add autodump metadata to models that are part of core django, add the following to one of your apps:

```python
# This will take the default fixture dumping config for this app and add the core auth.group and authtools.user
# tables to the groups and users fixtures respectively 
def get_autodump_labels(app_config, fixture):
    import allianceutils.management.commands.autodumpdata
    extras = {
        'groups': [
            'auth.group',
        ],
        'users': [
            'authtools.user',
        ],
    }
    return allianceutils.management.commands.autodumpdata.get_autodump_labels(app_config, fixture) + extras.get(fixture, [])
```


#### mysqlquickdump

FIXME

#### mysqlquickload

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

FIXME

### Middleware

#### CurrentUserMiddleware

* Middleware to enable accessing the currently logged-in user without a request object.
    * Properly handles multithreaded python by keeping track of the current user in a `dict` of `{'threadId': User}` 

* Setup
    * Add `allianceutils.middleware.CurrentUserMiddleware` to `MIDDLEWARE_CLASSES`.

* Usage

```python
from allianceutils.middleware import CurrentUserMiddleware

user = CurrentUserMiddleware.get_user()
```

### Migrations

FIXME

### Models

FIXME

### Serializers

#### JSON Ordered

* A version of django's core json serializer that outputs field in sorted order
* The built-in one uses a standard `dict` with completely unpredictable order which makes fixture diffs often contain field ordering changes

* Setup
    * Add to `SERIALIZATION_MODULES` in your settings
    * This will allow you to do fixture dumps with `--format json_ordered`
    * Note that django treats this as the file extension to use; `autodumpdata` overrides this to `.json`

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

* Requires `django-storages` and `boto` to be installed

* Use the below if you are using S3 for file storage and want to prefix media and / or static files - otherwise they will all be dumped unprefixed in the bucket.

* Configure S3 for use with S3 Boto

```python
AWS_ACCESS_KEY_ID = 'ACCESS_KEY'
AWS_STORAGE_BUCKET_NAME = 'bucket-name'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
```

#### StaticStorage

* An extension to S3BotoStorage that specifies a prefix for static files.
* Allows you to put static files and media files in S3 without worrying about clobbering each other.
* Note that if using on Heroku this doesn't play nice with pipelines so you probably don't want to use it
* Configuration

```python
STATICFILES_STORAGE = 'allianceutils.storage.StaticStorage'
STATICFILES_LOCATION="static"

STATIC_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, STATICFILES_LOCATION)
```

#### MediaStorage

* An extension to S3BotoStorage that specifies a prefix for static files.
* Allows you to put static files and media files in S3 without worrying about clobbering each other.

Configuration:

```python
DEFAULT_FILE_STORAGE = 'allianceutils.storage.MediaStorage'
MEDIAFILES_LOCATION="media"

MEDIA_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, MEDIAFILES_LOCATION)
```

### Template tags

#### script_json

* Dump a python object into json for embedding in a script tag

* Usage

```html
{% load script_json %}

<script>window.__APP_SETTINGS = {{ APP_SETTINGS|script_json }};</script>
```

#### alliance_bundle

* A wrapper to the webpack_bundle tag that accounts for the fact that
    * in production builds there will be separate JS + CSS files
    * in dev builds the CSS will be embedded in the webpack JS bundle
* Assumes that each JS file is paired with a CSS file.
    * If you are only including JS without extracted CSS then use `webpack_bundle`, or include a placeholder CSS bundle (will just include a webpack stub; if you are using `django-compress` then overhead from this will be minimal)

* Example Usage

```html
{% load alliance_bundle %}
<html>
<head>
  {% alliance_bundle 'shared-bower-jqueryui' 'css' %}
  {% alliance_bundle 'shared-bower-common' 'css' %}
  {% alliance_bundle 'shared-styles' 'css' %}
</head>
<body>
  
  ...
  
  {% alliance_bundle 'shared-bower-jqueryui' 'js' %}
  {% alliance_bundle 'shared-bower-common' 'js' %}
  {% alliance_bundle 'shared-styles' 'js' %}
</body>
</html>
```

* In production (`not settings.DEBUG`), the css tag will be a standard `<link rel="stylesheet" ...>` tag 
* In development (`settings.DEBUG`), the css tag will be a webpack JS inclusion that contains the CSS (and inherit webpack hotloading etc)

### Views 

#### JSONExceptionAPIView

FIXME

### Webpack

#### TimestampWebpackLoader

* Extension of WebpackLoader that appends a `?ts=(timestamp)` query string based on last modified time of chunk to serve.
* Allows static asset web server to send far future expiry headers without worrying about cache invalidation.

* Example usage

```python
WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'dist/prod/',
        'STATS_FILE': _Path(PROJECT_DIR, 'frontend/dist/prod/webpack-stats.json'),
        'LOADER_CLASS': 'allianceutils.webpack.TimestampWebpackLoader',
    },
}
```

## Changelog

* dev
* 0.1
    * 0.1.x
    * 0.1.6
        * Update `json_orminheritancefix` to work with django 1.11 
    * 0.1.5
        * Fix missing import if using autodumpdata automatically calculated filenames
        * autodumpdata now creates missing fixture directory automatically
    * 0.1.4
        * Fix bad versioning in previous release
    * 0.1.3
        * Added autodumpdata test cases
        * Added autodumpdata `--stdout`, `--output` options
        * Fix autodumpdata failing if `settings.SERIALIZATION_MODULES` not defined
    * 0.1.2
        * Added test cases, documentation
    * 0.1.1
        * Added StaticStorage, MediaStorage
    * 0.1.0
        * Initial release
