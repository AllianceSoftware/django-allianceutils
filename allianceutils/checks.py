from typing import Iterable
from typing import Mapping
from typing import Sequence

import django
from django.apps import apps
from django.apps.config import AppConfig
from django.core.checks import Warning
from django.db import models
from django.urls import get_resolver

from .management.commands.autodumpdata import get_autodump_labels

if django.VERSION >= (2, 0):
    from django.urls import URLResolver
else:
    from django.conf.urls import RegexURLResolver as URLResolver

# W001 not used
# W002 not used
# W003 not used
ID_WARNING_TRAILING_SLASH = 'allianceutils.W004'
ID_WARNING_AUTODUMP_MISSING = 'allianceutils.W005'
ID_WARNING_AUTODUMP_PROXY = 'allianceutils.W006'


def check_url_trailing_slash(expect_trailing_slash: bool, ignore_attrs: Mapping[str, Iterable[str]]={}):

    def _check_url_trailing_slash(app_configs: Sequence[AppConfig], **kwargs):
        # We ignore app_configs; so does django core check_url_settings()
        # Consider where ROOT_URLCONF points app A urlpatterns which include() app B urlpatterns
        # which define a URL to view in app C -- which app was the one that owned the URL?
        _ignore_attrs = {
            '_regex': [
                '^$',
            ],
            'lookup_str': [
                'django.views.static.serve',
            ],
            'app_name': [
                'admin',
                'djdt',
            ],
        }
        _ignore_attrs.update(ignore_attrs)

        def check_resolver(resolver: URLResolver, depth: int=0):
            warnings = []
            for url_pattern in resolver.url_patterns:

                # look
                if any(
                        getattr(url_pattern, attr, None) in vals or getattr(getattr(url_pattern, 'pattern', {}), attr, None) in vals
                        for attr, vals
                        in _ignore_attrs.items()):
                    continue

                try:
                    # django 2.0+ simplified urls (stilluses a regex underneath)
                    regex_pattern = url_pattern.pattern.regex.pattern
                except AttributeError:
                    # django <2.0 regex patterns
                    regex_pattern = url_pattern.regex.pattern

                if regex_pattern == '^$':
                    # empty patterns are a special case; they may be nested inside an
                    # include(), if that's the case then we don't really care whether
                    # they do or don't have a slash
                    continue

                if hasattr(url_pattern, 'url_patterns'):
                    # is a resolver, not a pattern: recurse
                    warnings.extend(check_resolver(url_pattern, depth+1))

                elif regex_pattern.endswith('/$') != expect_trailing_slash:
                    try:
                        # django 2.0+ simplified urls
                        description = url_pattern.pattern.describe()
                    except AttributeError:
                        # django <2.0 regex urls
                        description = url_pattern.describe()

                    warnings.append(
                        Warning(
                            'The URL pattern {} is inconsistent with expect_trailing_slash'.format(description),
                            obj=url_pattern,
                            id=ID_WARNING_TRAILING_SLASH,
                        )
                    )

            return warnings

        return check_resolver(get_resolver())
    return _check_url_trailing_slash


def warning_autodumpdata_missing(model: models.Model):
    """
    Create a missing autodumpdata definition warning
    """
    return Warning('Missing autodump definition',
        hint='see fixtures_autodump in alliance-django-utils README',
        obj=model,
        id=ID_WARNING_AUTODUMP_MISSING,
    )


def warning_autodumpdata_proxy(model: models.Model):
    """
    Create a missing autodumpdata definition warning
    """
    return Warning('Illegal proxy autodump definition',
        hint='fixtures_autodump(_sql) cannot be set on a proxy model',
        obj=model,
        id=ID_WARNING_AUTODUMP_PROXY,
    )


def check_autodumpdata(app_configs: Sequence[AppConfig], **kwargs):
    """
    Warn about models that don't have a fixtures_autodump or fixtures_autodump_sql attribute;
    see allianceutils.management.commands.autodumpdata
    """

    if app_configs is None:
        app_configs = apps.app_configs
    else:
        app_configs = {app_config.label: app_config for app_config in app_configs}
    check_app_labels = set(app_configs)

    known_models = {}
    proxy_models = set()
    recursed_models = set()
    valid_models = set()

    # find known models
    for app_config in app_configs.values():
        known_models.update({
            model._meta.label: model
            for model
            in app_config.get_models()
        })

    # mark models that have fixtures_autodump details
    for app_config in app_configs.values():
        for fixture, autodump_models in get_autodump_labels(app_config).items():
            valid_models.update(autodump_models.all())

    proxy_models = set([label for label, model in known_models.items() if model._meta.proxy])

    def process_model(model):
        label = model._meta.label

        # only process each model once
        if model in recursed_models:
            return
        recursed_models.add(model)

        # many:many relationship are included implicitly by dumpdata

    for model in known_models.values():
        process_model(model)

    # find models that weren't known
    errors_missing = set(known_models.keys()).difference(valid_models).difference(proxy_models)
    errors_missing = [
        warning_autodumpdata_missing(known_models[model_label])
        for model_label
        in sorted(errors_missing)
        if known_models[model_label]._meta.app_label in check_app_labels
    ]

    errors_proxy = []
    # proxy models should not explicitly define fixture details
    for model_label in sorted(proxy_models):
        model = known_models[model_label]
        proxied_model = model._meta.proxy_for_model
        if getattr(model, 'fixtures_autodump', None) is not getattr(proxied_model, 'fixtures_autodump', None) or \
            getattr(model, 'fixtures_autodump_sql', None) is not getattr(proxied_model, 'fixtures_autodump_sql', None):
            errors_proxy.append(warning_autodumpdata_proxy(model))

    return errors_missing + errors_proxy
