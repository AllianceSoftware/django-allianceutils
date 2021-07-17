from django.apps import AppConfig
from django.apps import apps

from isort.api import place_module


def is_firstparty_app(app_config: AppConfig):
    """
    Use isort's way of determining whether an app is "first party" or otherwise. exclude allianceutils.apps always (heroku detection's flawed otherwise)
    """
    return place_module(app_config.__module__) == 'FIRSTPARTY' or app_config.__module__ == 'allianceutils.apps'


def get_firstparty_apps():
    """
    Return all installed first party apps in an iterator
    """
    return filter(is_firstparty_app, apps.get_app_configs())
