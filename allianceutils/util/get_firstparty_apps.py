from django.apps import apps
from django.apps import AppConfig

from isort import SortImports

def is_firstparty_app(app_config: AppConfig):
    """
    Use isort's way of determining whether an app is "first party" or otherwise
    """
    return SortImports(file_contents='').place_module(app_config.__module__) == 'FIRSTPARTY'


def get_firstparty_apps():
    """
    Return all installed first party apps in an iterator
    """
    return filter(is_firstparty_app, apps.get_app_configs())
