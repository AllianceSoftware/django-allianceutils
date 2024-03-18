from __future__ import annotations

from distutils.util import strtobool
import hashlib
import os
from pathlib import Path
import random
import re
import sys
from typing import cast
import warnings

import django
from django.core.exceptions import ImproperlyConfigured

is_ci = os.environ.get('CI_SERVER', 'no') == 'yes'

BASE_DIR = Path(__file__).parent


def _build_db_settings():
    # Select DB engine
    engine = None

    db_type_to_backend = {
        "postgres": "django.db.backends.postgresql",
        "mysql": "django.db.backends.mysql",
    }

    if strtobool(os.environ.get('TOX', '0')):
        # look for the DB name in one of the tox environment name components
        engine_candidates = [
            backend
            for tox_env, backend
            in db_type_to_backend.items()
            if tox_env in str(Path(os.environ['VIRTUAL_ENV']).name).split('-')
        ]
        assert len(engine_candidates)
        engine = engine_candidates[0]

    # DB type is manually specified
    if engine is None and os.environ.get("DATABASE_TYPE"):
        engine = db_type_to_backend[os.environ["DATABASE_TYPE"]]

    # guess based on env variables & installed packages
    if engine is None and os.environ.get('PGDATABASE'):
        try:
            import psycopg2
        except ImportError:
            print("PGDATABASE set but pscyopg2 not installed", file=sys.stderr)
        else:
            engine = 'django.db.backends.postgresql'

    if engine is None:
        try:
            import MySQLdb
        except ImportError:
            pass
        else:
            engine = 'django.db.backends.mysql'

    if engine is None:
        raise ImproperlyConfigured("Can't detect database")

    # DB default settings
    db_vars_defaults = {
        'NAME': ('DB_NAME', 'alliance_django_utils'),
        'HOST': ('DB_HOST', 'localhost'),
        'PORT': ('DB_PORT', '5432' if engine == 'django.db.backends.postgresql' else '3306'),
        'USER': ('DB_USER', os.environ.get('USER', '') if engine == 'django.db.backends.postgresql' else None),
        'PASSWORD': ('DB_PASSWORD', None),
    }
    
    # override settings based on env vars
    db_vars: dict[str, str | dict[str, str] | None] = {
        var: os.environ.get(env_var, default)
        for var, (env_var, default)
        in db_vars_defaults.items()
    }
    # remove blank settings (no-password is not treated the same as '')
    db_vars = {key: value for key, value in db_vars.items() if value}
    
    db_vars['ENGINE'] = engine
    
    if engine == 'django.db.backends.mysql':
        # extra mysql options
        db_options = {
            'init_command': 'SET default_storage_engine=INNODB',
            'charset': 'utf8mb4',
        }
        if not is_ci:
            db_options['read_default_file'] = '~/.my.cnf'

        db_vars['OPTIONS'] = db_options

    return db_vars


# Django connects via the live DB in order to create/drop the test DB
# If the live DB doesn't exist then it bails out before even trying to
# create the test DB, so this doesn't really work
# if is_ci:
#     db_vars['TEST'] = {
#         'NAME': db_vars['NAME'],
#     }

DATABASES = {'default': _build_db_settings()}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

INSTALLED_APPS = (
    'allianceutils',
    'test_allianceutils',
    'test_allianceutils.tests.checks_explicit_table_names',
    'test_allianceutils.tests.checks_field_names',
    'test_allianceutils.tests.document_reverse_accessors',
    'test_allianceutils.tests.middleware',
    'test_allianceutils.tests.profile_auth',
    'test_allianceutils.tests.serializers',
    'test_allianceutils.tests.viewset_permissions',

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
)

AUTH_USER_MODEL = 'profile_auth.User'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

MIDDLEWARE = ()

TEMPLATE_DIRS = (
    # os.path.join(BASE_DIR, 'compat/tests/templates/')
)

TEMPLATES = (
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': TEMPLATE_DIRS,
    },
)

STATIC_ROOT = Path(BASE_DIR, 'static')

SERIALIZATION_MODULES = {
    'json_ordered': 'allianceutils.serializers.json_ordered',
}

ROOT_URLCONF = 'test_allianceutils.urls'

SECRET_KEY = hashlib.sha256(str(random.SystemRandom().getrandbits(256)).encode('ascii')).hexdigest()

USE_TZ = True

# -------------------------------------
# Test case performance
PASSWORD_HASHERS = (
        #'django_plainpasswordhasher.PlainPasswordHasher', # very fast but extremely insecure
        "django.contrib.auth.hashers.SHA1PasswordHasher",  # fast but insecure
    )

# -------------------------------------
# Custom settings
QUERY_COUNT_WARNING_THRESHOLD = 40

warnings.simplefilter('always')

try:
    from django.utils.deprecation import RemovedInDjango51Warning
except ImportError:
    pass
else:
    # SHA1Passwordhasher might be on its way out but it is still good for test cases because it's
    # much faster than the (secure) alternatives
    warnings.filterwarnings(
        "ignore",
        category=PendingDeprecationWarning,
        message="django.contrib.auth.hashers.SHA1PasswordHasher is deprecated.",
    )
