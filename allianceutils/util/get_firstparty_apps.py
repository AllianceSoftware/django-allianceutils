import os
import sys

from django.apps import AppConfig
from django.apps import apps
from isort.api import Config
from isort.api import place_module

# we don't use __main__.__file__ because debugging in an IDE (eg pycharm) __main__ may be the IDE's setup script
# os.getcwd() should be safe since django's manage.py insists on running in the django root
isort_config = Config(settings_path=os.getcwd())


def is_firstparty_app(app_config: AppConfig):
    """
    Use isort's way of determining whether an app is "first party" or otherwise
    """
    module_name = app_config.module.__name__
    return place_module(module_name, config=isort_config) == 'FIRSTPARTY'
       # this shouldn't be needed anymore now that we specify the isort config:
       # or app_config.__module__ == 'allianceutils.apps'


def get_firstparty_apps():
    """
    Return all installed first party apps in an iterator
    """
    return filter(is_firstparty_app, apps.get_app_configs())
