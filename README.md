# Alliance Utils

A collection of utilities for django projects.

* [Installation](#installation)
* [Package](#package)
    * [Commands](#commands)
    * [Views](#views)
    * [Decorators](#decorators)
    * [Filters](#filters)
    * [Middleware](#middleware)
    * [Migrations](#migrations)
    * [API](#api)
    * [Models](#models)
    * [Auth](#auth)
    * [Webpack](#webpack)
    * [Serializers](#serializers)

## Installation

`pip install -e git+git@gitlab.internal.alliancesoftware.com.au:alliance/alliance-django-utils.git@master#egg=allianceutils`

## Package

### Commands

#### autodumpdata
#### mysqlquickdump
#### mysqlquickload

### Views 

#### JSONExceptionAPIView

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

### API

### Models

### Auth

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

### Serializers

#### JSON Ordered

A version of django's core json serializer that outputs field in sorted order
(the built-in one uses a standard dict() with completely unpredictable order which makes fixture diffs often contain field ordering changes).

* Setup

Add to `SERIALIZATION_MODULES` in your settings.

```
SERIALIZATION_MODULES = {
    'json_ordered': 'allianceutils.serializers.json_ordered',
}
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

### Management

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
