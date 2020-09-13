import ast
from collections import defaultdict
import inspect
from pathlib import Path
import re
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Type

import django
from django.apps import apps
from django.apps.config import AppConfig
from django.conf import settings
from django.core.checks import Error
from django.core.checks import Warning
from django.db.models import Model
from django.urls import get_resolver

from allianceutils.util import camel_to_underscore
from allianceutils.util import get_firstparty_apps
from allianceutils.util import underscore_to_camel

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
#ID_WARNING_AUTODUMP_MISSING = 'allianceutils.W005'
#ID_WARNING_AUTODUMP_PROXY = 'allianceutils.W006'
ID_WARNING_GIT = 'allianceutils.W007'
ID_WARNING_GIT_HOOKS = 'allianceutils.W008'
ID_ERROR_GIT_HOOKS = 'allianceutils.E008'
ID_ERROR_EXPLICIT_TABLE_NAME = 'allianceutils.E009'
ID_ERROR_EXPLICIT_TABLE_NAME_LOWERCASE = 'allianceutils.E010'
ID_ERROR_FIELD_NAME_NOT_CAMEL_FRIENDLY = 'allianceutils.E011'


def find_candidate_models(
        app_configs: Optional[Iterable[AppConfig]],
        ignore_labels: Iterable[str] = None
) -> Dict[str, Type[Model]]:
    """
    Given a list of labels to ignore, return models whose app_label or label is NOT in ignore_labels.
    :return: dict which is a mapping of candidate models in the format of { model_label: Model }
    """
    if app_configs is None:
        app_configs = get_firstparty_apps()

    if ignore_labels is None:
        ignore_labels = []

    ignore_labels = set(ignore_labels)
    candidate_models: Dict[str, Type[Model]] = {}

    for app_config in app_configs:
        candidate_models.update({
            model._meta.label: model
            for model
            in app_config.get_models()
            if model._meta.app_label not in ignore_labels and model._meta.label not in ignore_labels
        })

    return candidate_models


class CheckUrlTrailingSlash:
    expect_trailing_slash: bool
    ignore_attrs: Mapping[str, Iterable[str]]

    def __init__(self, expect_trailing_slash: bool, ignore_attrs: Mapping[str, Iterable[str]]={}):
        self.expect_trailing_slash = expect_trailing_slash
        self.ignore_attrs = ignore_attrs

    def __call__(self, app_configs: Iterable[AppConfig], **kwargs):
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
        _ignore_attrs.update(self.ignore_attrs)

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

                elif regex_pattern.endswith('/$') != self.expect_trailing_slash:
                    try:
                        # django 2.0+ simplified urls
                        description = url_pattern.pattern.describe()
                    except AttributeError:
                        # django <2.0 regex urls
                        description = url_pattern.describe()

                    warnings.append(
                        Warning(
                            f'The URL pattern {description} is inconsistent with expect_trailing_slash',
                            obj=url_pattern,
                            id=ID_WARNING_TRAILING_SLASH,
                        )
                    )

            return warnings

        return check_resolver(get_resolver())


def check_git_hooks(app_configs: Iterable[AppConfig], **kwargs):
    git_path = Path(settings.PROJECT_DIR, '.git')

    # handle the case where .git is a file rather than a directory
    try:
        with git_path.open() as f:
            git_path = Path(f.readline())
    except OSError:
        pass

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
        precommit = git_hooks_path / 'pre-commit'

        found_installed_hooks = False
        if git_hooks_path.is_symlink():
            found_installed_hooks = True
        else:
            try:
                with precommit.open('r') as f:
                    first_two_lines = next(f), next(f)
                    if first_two_lines == ('#!/bin/sh\n', '# husky\n'):
                        found_installed_hooks = True
            except (FileNotFoundError, StopIteration):
                pass

        if not found_installed_hooks:
            (warning_type, warning_id) = (Error, ID_ERROR_GIT_HOOKS) if settings.DEBUG else (Warning, ID_WARNING_GIT_HOOKS)
            warnings.append(
                warning_type(
                    "git hooks are not configured (husky should be installed or .git/hooks should be a symlink to the git-hooks directory)",
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

def _check_explicit_table_names_on_model(model: Type[Model], enforce_lowercase: bool) -> Iterable[Type[Error]]:
    """
    Use an ast to check if a model has the db_table meta option set.
    This is done this way because a model instance's db_table is always
    populated even if with that of the default.
    """
    errors = []
    found = None
    tree = ast.parse(inspect.getsource(model))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'Meta':
            for sub_node in node.body:
                if isinstance(sub_node, ast.Assign):
                    if sub_node.targets[0].id == 'db_table':
                        found = sub_node.value.s
                        break
    if not found:
        errors.append(
            Error(
                'Explicit table name required',
                hint=f'Add db_table setting to {model._meta.label} model Meta',
                obj=model,
                id=ID_ERROR_EXPLICIT_TABLE_NAME,
            )
        )
    elif enforce_lowercase and not found.islower():
        errors.append(
            Error(
                'Table names must be lowercase',
                hint=f'Check db_table setting for {model._meta.label}',
                obj=model,
                id=ID_ERROR_EXPLICIT_TABLE_NAME_LOWERCASE,
            )
        )

    return errors


DEFAULT_TABLE_NAME_CHECK_IGNORE = [
    'auth',
]


class CheckExplicitTableNames:
    """
    A check for models with missing or invalid db_table settings
    """

    ignore_labels: Iterable[str]
    enforce_lowercase: bool

    def __init__(self, ignore_labels: Iterable[str] = DEFAULT_TABLE_NAME_CHECK_IGNORE, enforce_lowercase: bool = True):
        """
        ignore_labels: ignore apps or models matching supplied labels
        enforce_lowercase: applies rule E010 which enforces table name to be all lowercase; defaults to True
        """
        self.ignore_labels = ignore_labels
        self.enforce_lowercase = enforce_lowercase

    def __call__(self, app_configs: Iterable[AppConfig], **kwargs):
        """
        Warn when models don't have Meta's db_table_name set in apps that require it.
        """
        candidate_models = find_candidate_models(app_configs, self.ignore_labels)
        errors = []
        for model in candidate_models.values():
            errors += _check_explicit_table_names_on_model(model, self.enforce_lowercase)
        return errors


class CheckReversibleFieldNames:
    ignore_labels: Iterable[str]

    def __init__(self, ignore_labels: Iterable[str] = []):
        self.ignore_labels = ignore_labels

    def __call__(self, app_configs: Iterable[AppConfig], ** kwargs):
        candidate_models = find_candidate_models(app_configs, self.ignore_labels)
        errors = []
        for model in candidate_models.values():
            errors += self._check_field_names_on_model(model)
        return errors

    def _check_field_names_on_model(self, model: Type[Model]) -> Iterable[Type[Error]]:
        """
        check whether field names on model are legit

        currently contains only one check:
        1. checks whether field name contains any number preceded by an underscore. the underscore will be lost when
           camelized then de-camelized again. Since camelize is performed automatically to/from frontend it leads to bugs.

        """

        errors = []

        for field in model._meta.fields:
            if camel_to_underscore(underscore_to_camel(field.name)) != field.name:
                hint = None
                if re.search(r'_[0-9]', field.name):
                    hint = f'Underscore before a number in {model._meta.label}.{field.name}'
                errors.append(
                    Error(
                        f"Field name is not reversible with underscore_to_camel()/camel_to_underscore()",
                        hint=hint,
                        obj=model,
                        id=ID_ERROR_FIELD_NAME_NOT_CAMEL_FRIENDLY,
                    )
                )

        return errors