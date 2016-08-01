"""
This script is a trick to setup a fake Django environment, since this reusable
app will be developed and tested outside any specific Django project.
Via ``settings.configure`` you will be able to set all necessary settings
for your app and run the tests as if you were calling ``./manage.py test``.

Adapted from django-compat
"""
from __future__ import print_function

import os
import sys

import django

is_ci = os.environ.get('CI_SERVER', 'no') == 'yes'

def setup():
    BASE_DIR = os.path.dirname(__file__)

    db_vars = {
        'HOST': ('MYSQL_HOST', None),
        'USER': ('MYSQL_USER', None),
        'PASSWORD': ('MYSQL_PASSWORD', None),
        'NAME': ('MYSQL_DATABASE', 'alliancedjangoutils'),
    }
    db_vars = { var: os.environ.get(env_var, default) for var, (env_var, default) in db_vars.items() }
    db_vars = { key: value for key, value in db_vars.items() if value }
    db_vars['ENGINE'] = 'django.db.backends.mysql'
    db_vars['OPTIONS'] = {
        'init_command': 'SET default_storage_engine=InnoDB',
        'read_default_file': '~/.my.cnf',
    }

    if is_ci:
        db_vars['TEST'] = {
            'NAME': db_vars['NAME'],
        }

    DATABASES = { 'default': db_vars }

    INSTALLED_APPS = [
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'allianceutils',
        'allianceutils.tests.serializers',
    ]

    MIDDLEWARE_CLASSES = []

    TEMPLATE_DIRS = [
        # os.path.join(BASE_DIR, 'compat/tests/templates/')
    ]

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'APP_DIRS': True,
            'DIRS': TEMPLATE_DIRS,
        },
    ]

    SERIALIZATION_MODULES = {
        'json_ordered': 'allianceutils.serializers.json_ordered',
        'json': 'allianceutils.serializers.json_orminheritancefix',
    }

    from django.conf import settings

    if not settings.configured:
        settings.configure(
            INSTALLED_APPS=INSTALLED_APPS,
            DATABASES=DATABASES,
            ROOT_URLCONF='allianceutils.tests.urls',
            MIDDLEWARE_CLASSES=MIDDLEWARE_CLASSES,
            TEMPLATE_DIRS=TEMPLATE_DIRS,
            TEMPLATES=TEMPLATES,
            SERIALIZATION_MODULES=SERIALIZATION_MODULES,
        )


def runtests(*test_args):

    django.setup()

    import django_nose  # has to be imported after django config happens

    runner = django_nose.NoseTestSuiteRunner(
        verbosity=2,
        interactive=not is_ci
    )
    failures = runner.run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    setup()
    runtests(*sys.argv[1:])
