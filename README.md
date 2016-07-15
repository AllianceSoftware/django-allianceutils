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

## Installation

`pip install -e git+git@gitlab.internal.alliancesoftware.com.au:alliance/alliance-django-utils.git@master#egg=allianceutils`

## Usage

### API

FIXME

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
# tables to the groups and users fixtures respsectively 
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

Search for a string across multiple fields. Requires django_filters.

* Usage 

```
from allianceutils.filters import MultipleFieldCharFilter

# ...
# In your filter set (see django_filters for documentation)
customer = MultipleFieldCharFilter(names=('customer__first_name', 'customer__last_name'), lookup_expr='icontains')
```

### Management

FIXME

### Middleware

#### CurrentUserMiddleware

Middleware to enable accessing the currently logged-in user without a request object.

* Setup

Add `allianceutils.middleware.CurrentUserMiddleware` to MIDDLEWARE_CLASSES.

* Usage

```
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
    * CURRENTLY THIS ONLY WORKS FOR DJANGO 1.8
* We need to replace not only the serializer but also the deserializer

```python
SERIALIZATION_MODULES = {
    'json': 'allianceutils.serializers.json_orminheritancefix',
}
```

### Storage

Use the below if you are using S3 for file storage and want to prefix media and
/ or static files - otherwise they will all be dumped unprefixed in the bucket.

Configure S3 for use with S3 Boto:

```python
AWS_ACCESS_KEY_ID = 'ACCESS_KEY'
AWS_STORAGE_BUCKET_NAME = 'bucket-name'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
```


#### StaticStorage

This is an extension to S3BotoStorage that specifies a prefix for static files.
This allows you to put static files and media files in S3 without worrying
about clobbering each other.

Configuration:

```python
STATICFILES_STORAGE = 'allianceutils.storage.StaticStorage'
STATICFILES_LOCATION="static"

STATIC_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, STATICFILES_LOCATION)
```

#### MediaStorage

This is an extension to S3BotoStorage that specifies a prefix for static files.
This allows you to put static files and media files in S3 without worrying
about clobbering each other.

Configuration:

```python
DEFAULT_FILE_STORAGE = 'allianceutils.storage.MediaStorage'
MEDIAFILES_LOCATION="media"

MEDIA_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, MEDIAFILES_LOCATION)
```

### Template tags

#### script_json

* Usage

In your template:
```
{% load script_json %}

<script>window.__APP_SETTINGS = {{ APP_SETTINGS|script_json }};</script>
```

#### alliance_bundle

FIXME

### Views 

#### JSONExceptionAPIView

FIXME

### Webpack

#### TimestampWebpackLoader

Extension of WebpackLoader that appends a ?ts=(timestamp) query string based on last modified time of chunk to serve.

Allows static asset web server to send far future expiry headers without worrying about cache invalidation.

* Setup

Set the `LOADER_CLASS` key in `WEBPACK_LOADER` config to `allianceutils.webpack.TimestampWebpackLoader`. eg.

```
WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'dist/prod/',
        'STATS_FILE': _Path(PROJECT_DIR, 'frontend/dist/prod/webpack-stats.json'),
        'LOADER_CLASS': 'allianceutils.webpack.TimestampWebpackLoader',
    },
}
```
