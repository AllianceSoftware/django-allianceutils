import hashlib as _hashlib
import os as _os
from pathlib import Path as _Path
import random as _random
import warnings as _warnings

is_ci = _os.environ.get('CI_SERVER', 'no') == 'yes'

BASE_DIR = _Path(__file__).parent

_db_vars = {
    'NAME': ('DB_NAME', 'alliance_django_utils'),
    'HOST': ('DB_HOST', 'localhost'),
    'PORT': ('DB_PORT', '5432'),
    'USER': ('DB_USER', _os.environ.get('USER', '')),
    'PASSWORD': ('DB_PASSWORD', None),
}
_db_vars = {var: _os.environ.get(env_var, default) for var, (env_var, default) in _db_vars.items()}
_db_vars = {key: value for key, value in _db_vars.items() if value}
_db_vars['ENGINE'] = 'django.db.backends.postgresql'

# Django connects via the live DB in order to create/drop the test DB
# If the live DB doesn't exist then it bails out before even trying to
# create the test DB, so this doesn't really work
# if is_ci:
#     db_vars['TEST'] = {
#         'NAME': db_vars['NAME'],
#     }

DATABASES = {'default': _db_vars}

INSTALLED_APPS = (
    'allianceutils',
    'authtools',
    'test_allianceutils',
    'test_allianceutils.tests.middleware',
    'test_allianceutils.tests.profile_auth',
    'test_allianceutils.tests.serializers',
    'test_allianceutils.tests.checks_db_constraints',
    'test_allianceutils.tests.document_reverse_accessors',
    'test_allianceutils.tests.checks_explicit_table_names',

    'django_db_constraints',

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
)

AUTH_USER_MODEL = 'profile_auth.User'
AUTHENTICATION_BACKENDS = [
    'allianceutils.auth.backends.ProfileModelBackend',
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

STATIC_ROOT = _Path(BASE_DIR, 'static')

SERIALIZATION_MODULES = {
    'json_ordered': 'allianceutils.serializers.json_ordered',
    'json': 'allianceutils.serializers.json_orminheritancefix',
}

ROOT_URLCONF = 'test_allianceutils.urls'

SECRET_KEY = _hashlib.sha256(str(_random.SystemRandom().getrandbits(256)).encode('ascii')).hexdigest()

QUERY_COUNT_WARNING_THRESHOLD = 40

_warnings.simplefilter('always')
