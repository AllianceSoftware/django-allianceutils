from __future__ import annotations

import os
from typing import Iterable

from django.apps import AppConfig
from django.apps import apps

# we don't use __main__.__file__ because debugging in an IDE (eg pycharm) __main__ may be the IDE's setup script
# os.getcwd() should be safe since django's manage.py insists on running in the django root
#
# take a copy of the current working directory asap in case something else changes it
_root_path = os.getcwd()


def is_firstparty_app(app_config: AppConfig) -> bool:
    """
    Use isort's way of determining whether an app is "first party" or otherwise
    """
    # import isort here so that it's not a hard dependency
    from isort.api import Config
    from isort.api import place_module

    isort_config = Config(settings_path=_root_path)

    assert app_config.module is not None
    module_name = app_config.module.__name__
    return place_module(module_name, config=isort_config) == 'FIRSTPARTY'
       # this shouldn't be needed anymore now that we specify the isort config:
       # or app_config.__module__ == 'allianceutils.apps'


def get_firstparty_apps() -> Iterable[AppConfig]:
    """
    Return all installed first party apps in an iterator
    """
    return filter(is_firstparty_app, apps.get_app_configs())
