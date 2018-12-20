from collections import defaultdict
from pathlib import Path
from typing import Dict
from typing import Iterable
from typing import Mapping
from typing import Set
from typing import Type

import django
from django.apps import apps
from django.apps.config import AppConfig
from django.conf import settings
from django.core.checks import Error
from django.core.checks import Warning
from django.db import models
from django.db.models import Model
from django.urls import get_resolver

from .management.commands.autodumpdata import get_autodump_labels

if django.VERSION >= (2, 0):
    from django.urls import URLResolver
else:
    from django.conf.urls import RegexURLResolver as URLResolver

# W001 not used
# W002 not used
# W003 not used
ID_ERROR_PROFILE_RELATED_TABLES = 'allianceutils.E001'
ID_ERROR_DB_CONSTRAINTS = 'allianceutils.E002'
ID_ERROR_ADMINS = 'allianceutils.E003'
ID_WARNING_TRAILING_SLASH = 'allianceutils.W004'
ID_WARNING_AUTODUMP_MISSING = 'allianceutils.W005'
ID_WARNING_AUTODUMP_PROXY = 'allianceutils.W006'
ID_WARNING_GIT = 'allianceutils.W007'
ID_WARNING_GIT_HOOKS = 'allianceutils.W008'
ID_ERROR_GIT_HOOKS = 'allianceutils.E008'


def check_url_trailing_slash(expect_trailing_slash: bool, ignore_attrs: Mapping[str, Iterable[str]]={}):

    def _check_url_trailing_slash(app_configs: Iterable[AppConfig], **kwargs):
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


def make_check_autodumpdata(ignore_labels: Iterable[str]):
    """
    Return a function that checks for models with missing autodumpdata definitions

    Args:
        ignore_labels:

    Returns:
        check function for use with django system checks
    """
    ignore_labels = set(ignore_labels)

    def check_autodumpdata(app_configs: Iterable[AppConfig], **kwargs):
        """
        Warn about models that don't have a fixtures_autodump or fixtures_autodump_sql attribute;
        see allianceutils.management.commands.autodumpdata
        """

        if app_configs is None:
            app_configs = apps.app_configs
        else:
            app_configs = {app_config.label: app_config for app_config in app_configs}
        check_app_labels = set(app_configs.keys())

        candidate_models: Dict[str, Type[Model]] = {}
        valid_models: Set[str] = set()

        # find candidate models
        for app_config in app_configs.values():
            candidate_models.update({
                model._meta.label: model
                for model
                in app_config.get_models()
                if model._meta.app_label not in ignore_labels and model._meta.label not in ignore_labels
            })

        # mark models that have fixtures_autodump details
        for app_config in app_configs.values():
            for fixture, autodump_models in get_autodump_labels(app_config).items():
                valid_models.update(autodump_models.all())

        proxy_models: Set[str] = set([label for label, model in candidate_models.items() if model._meta.proxy])

        # many:many relationships are included implicitly by dumpdata from the table they're declared on,
        # so mark these as okay.
        # Known issue: If you are only looking at one app_config then it will not see implict inclusions from
        # other apps
        # The implicit inclusion is not transitive (we don't need to recurse into the included tables)
        implicit_models = set()
        for model_label in valid_models:
            try:
                model = candidate_models[model_label]
            except KeyError:
                continue
            for field in model._meta.get_fields(include_hidden=True): # need to include hidden to get automatically created through models
                try:
                    if field.is_relation and field.many_to_many:
                        through = field.remote_field.through
                        implicit_models.add(through._meta.label)
                except AttributeError:
                    pass

        # TODO: how should GenericForeignKeys be handled?

        # find models that were missing autodumpdata definitions
        errors_missing = set(candidate_models.keys()) \
            .difference(valid_models) \
            .difference(proxy_models) \
            .difference(implicit_models)
        errors_missing = [
            warning_autodumpdata_missing(candidate_models[model_label])
            for model_label
            in sorted(errors_missing)
            if candidate_models[model_label]._meta.app_label in check_app_labels
        ]

        errors_proxy = []
        # proxy models should not explicitly define fixture details
        for model_label in sorted(proxy_models):
            model = candidate_models[model_label]
            proxied_model = model._meta.proxy_for_model
            if getattr(model, 'fixtures_autodump', None) is not getattr(proxied_model, 'fixtures_autodump', None) or \
                    getattr(model, 'fixtures_autodump_sql', None) is not getattr(proxied_model, 'fixtures_autodump_sql', None):
                errors_proxy.append(warning_autodumpdata_proxy(model))

        return errors_missing + errors_proxy

    return check_autodumpdata


DEFAULT_AUTODUMP_CHECK_IGNORE = [
    'silk',
]
check_autodumpdata = make_check_autodumpdata(DEFAULT_AUTODUMP_CHECK_IGNORE)


def check_git_hooks(app_configs: Iterable[AppConfig], **kwargs):
    git_path = Path(settings.PROJECT_DIR, '.git')

    warnings = []

    if not git_path.exists():
        if settings.DEBUG:
            # If in dev mode then there should be a .git dir
            warnings.append(
                Warning(
                    "DEBUG is true but can't find a .git dir; are you trying to use DEBUG in production?",
                    obj=git_path,
                    id=ID_WARNING_GIT,
                )
            )
    else:
        # there is a .git dir:
        #   If dev then there must be a .git/hooks symlink
        #   If in prod then there should be a .git/hooks symlink if there is a .git dir
        git_hooks_path = Path(git_path, 'hooks')
        if not git_hooks_path.is_symlink():
            (warning_type, warning_id) = (Error, ID_ERROR_GIT_HOOKS) if settings.DEBUG else (Warning, ID_WARNING_GIT_HOOKS)
            warnings.append(
                warning_type(
                    ".git/hooks should be a symlink to the git-hooks directory",
                    obj=git_hooks_path,
                    id=warning_id,
                )
            )

    return warnings


def check_admins(app_configs: Iterable[AppConfig], **kwargs):
    errors = []
    if not settings.AUTOMATED_TESTS and not settings.DEBUG:
        if len(settings.ADMINS) == 0:
            errors.append(
                Error(
                    "settings.ADMINS should not be empty",
                    obj='settings',
                    id=ID_ERROR_ADMINS,
                )
            )
    return errors


def check_db_constraints(app_configs: Iterable[AppConfig], **kwargs):
    """
    If using django-db-constraints, constraint identifiers can be supplied
    that are longer than the max identifier length for Postgres
    (63 bytes, see https://stackoverflow.com/a/8218026/6653190) or MySQL
    (64 BMP unicode characters, see https://dev.mysql.com/doc/refman/8.0/en/identifiers.html).
    Check that any such constraints are globally unique when truncated to the smaller (Postgres) limit.
    """
    if app_configs is None:
        app_configs = apps.app_configs
    else:
        app_configs = {app_config.label: app_config for app_config in app_configs}

    NAMEDATALEN = 63

    def _truncate_constraint_name(_name):
        return _name.encode('utf-8')[:NAMEDATALEN]

    known_constraints = defaultdict(list)
    for app_config in app_configs.values():
        for model in app_config.get_models():
            if hasattr(model._meta, 'db_constraints'):
                for constraint_name in model._meta.db_constraints.keys():
                    known_constraints[_truncate_constraint_name(constraint_name)].append((model, constraint_name))

    errors = []
    for truncated_name, model_constraints in known_constraints.items():
        if len(model_constraints) == 1:
            continue
        _models = ['%s.%s' % (model._meta.app_label, model.__name__) for model, _ in model_constraints]
        models_string = ', '.join(_models)
        for _model, constraint_name in model_constraints:
            errors.append(
                Error(
                    '%s constraint %s is not unique' % (_model._meta.label, constraint_name),
                    hint='Constraint truncates to %s' % truncated_name.decode('utf-8', 'replace'),
                    obj=models_string,
                    id=ID_ERROR_DB_CONSTRAINTS,
                )
            )

    return errors
