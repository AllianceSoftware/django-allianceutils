# Alliance Utils

A collection of utilities for django projects.

## Installation

`pip install git+git@gitlab.internal.alliancesoftware.com.au:alliance/alliance-django-utils.git@master#egg=allianceutils`

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