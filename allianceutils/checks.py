import ast
from collections import defaultdict
import inspect
from pathlib import Path
import re
import subprocess
from typing import Dict
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Type
from typing import Union

from django.apps import apps
from django.apps.config import AppConfig
from django.conf import settings
from django.core.checks import CheckMessage
from django.core.checks import Error
from django.core.checks import Info
from django.core.checks import Warning
from django.db.models import Model
from django.urls import get_resolver
from django.urls import URLResolver

from allianceutils.util import camel_to_underscore
from allianceutils.util import get_firstparty_apps
from allianceutils.util import underscore_to_camel

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
ID_INFO_EXPLICIT_TABLE_NAME_LOWERCASE = 'allianceutils.I010'
ID_ERROR_FIELD_NAME_NOT_CAMEL_FRIENDLY = 'allianceutils.E011'

try:
    Pattern = re.Pattern
except AttributeError:
    # Until python 3.7 re.Pattern was not exposed (was only present internally as _pattern_type)
    Pattern = object


def find_candidate_models(
    app_configs: Optional[Iterable[AppConfig]],
    ignore_labels: Iterable[Union[str, Pattern]] = None
) -> Dict[str, Type[Model]]:
    """
    Given a list of labels to ignore, return models whose app_label or label is NOT in ignore_labels.
    :return: dict which is a mapping of candidate models in the format of { model_label: Model }
    """
    if app_configs is None:
        app_configs = get_firstparty_apps()

    if ignore_labels is None:
        ignore_labels = []

    def should_ignore(label: str) -> bool:
        return (
            # string match
            any(s == label for s in ignore_labels) or
            # regex pattern match
            any(p.match(label) for p in ignore_labels if hasattr(p, "match"))
        )

    candidate_models: Dict[str, Type[Model]] = {}

    for app_config in app_configs:
        candidate_models.update({
            model._meta.label: model
            for model
            in app_config.get_models()
            if not should_ignore(model._meta.app_label) and not should_ignore(model._meta.label)
        })

    return candidate_models


class CheckUrlTrailingSlash:
    expect_trailing_slash: bool
    ignore_attrs: Mapping[str, Iterable[str]]

    def __init__(self, expect_trailing_slash: bool, ignore_attrs: Mapping[str, Iterable[str]] = {}):
        self.expect_trailing_slash = expect_trailing_slash
        self.ignore_attrs = ignore_attrs

    def __call__(self, app_configs: Iterable[AppConfig], **kwargs) -> List[CheckMessage]:
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

        def check_resolver(resolver: URLResolver, depth: int = 0) -> List[CheckMessage]:
            messages = []
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

                if regex_pattern == r'^\Z' or regex_pattern == '^$':
                    # empty patterns are a special case; they may be nested inside an
                    # include(), if that's the case then we don't really care whether
                    # they do or don't have a slash
                    continue

                if hasattr(url_pattern, 'url_patterns'):
                    # is a resolver, not a pattern: recurse
                    messages.extend(check_resolver(url_pattern, depth+1))
                elif (regex_pattern.endswith('/$') or regex_pattern.endswith(r'/\Z')) != self.expect_trailing_slash:
                    try:
                        # django 2.0+ simplified urls
                        description = url_pattern.pattern.describe()
                    except AttributeError:
                        # django <2.0 regex urls
                        description = url_pattern.describe()

                    messages.append(
                        Warning(
                            f'The URL pattern {description} is inconsistent with expect_trailing_slash',
                            obj=url_pattern,
                            id=ID_WARNING_TRAILING_SLASH,
                        )
                    )

            return messages

        return check_resolver(get_resolver())


class CheckGitHooks:
    git_path: Optional[Union[str, Path]] = None

    def __init__(self, git_path: Optional[Union[str, Path]] = None):
        self.git_path = Path(git_path) or get_default_git_path()

    def __call__(self, app_configs: Iterable[AppConfig], **kwargs):
        return _check_git_hooks(app_configs, self.git_path, **kwargs)


def get_default_git_path() -> str:
    return Path(settings.PROJECT_DIR, '.git')


def check_git_hooks(app_configs: Iterable[AppConfig], **kwargs) -> List[CheckMessage]:
    return _check_git_hooks(app_configs, git_path=get_default_git_path(), **kwargs)


def _check_git_hooks(app_configs: Iterable[AppConfig], git_path: Path, **kwargs) -> List[CheckMessage]:

    # handle the case where .git is a file rather than a directory
    try:
        with git_path.open() as f:
            git_path = Path(f.readline())
    except OSError:
        pass

    messages = []

    if not git_path.exists():
        if settings.DEBUG:
            # If in dev mode then there should be a .git dir
            messages.append(
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

        # Check the git config for a hooksPath setting (now used by husky)
        git_config_result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            capture_output=True,
            cwd=git_path,
        )
        if not git_config_result.returncode:
            git_hooks_path = Path(git_config_result.stdout.decode('utf-8').strip('\n'))
            if not git_hooks_path.is_absolute():
                git_hooks_path = Path(settings.PROJECT_DIR) / git_hooks_path

        precommit = git_hooks_path / 'pre-commit'

        found_installed_hooks = False
        if git_hooks_path.is_symlink():
            found_installed_hooks = True
        else:
            try:
                with precommit.open('r') as f:
                    first_two_lines = next(f), next(f)
                    husky_pre_commits = [
                        ('#!/bin/sh\n', '# husky\n'),
                        ('#!/bin/sh\n', '. "$(dirname "$0")/_/husky.sh"\n'),
                    ]
                    if first_two_lines in husky_pre_commits:
                        found_installed_hooks = True
            except (FileNotFoundError, StopIteration):
                pass

        if not found_installed_hooks:
            (warning_type, warning_id) = (Error, ID_ERROR_GIT_HOOKS) if settings.DEBUG else (Warning, ID_WARNING_GIT_HOOKS)
            messages.append(
                warning_type(
                    "git hooks are not configured (husky should be installed or .git/hooks should be a symlink to the git-hooks directory)",
                    obj=git_hooks_path,
                    id=warning_id,
                )
            )

    return messages


def check_admins(app_configs: Iterable[AppConfig], **kwargs) -> List[CheckMessage]:
    messages = []
    if not settings.AUTOMATED_TESTS and not settings.DEBUG:
        if len(settings.ADMINS) == 0:
            messages.append(
                Error(
                    "settings.ADMINS should not be empty",
                    obj='settings',
                    id=ID_ERROR_ADMINS,
                )
            )
    return messages


def check_db_constraints(app_configs: Iterable[AppConfig], **kwargs) -> List[CheckMessage]:
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
            # native django constraints
            if hasattr(model._meta, 'constraints'):
                for constraint in model._meta.constraints:
                    known_constraints[_truncate_constraint_name(constraint.name)].append((model, constraint.name))
            # constraints from the django-db-constraints package
            if hasattr(model._meta, 'db_constraints'):
                for constraint_name in model._meta.db_constraints.keys():
                    known_constraints[_truncate_constraint_name(constraint_name)].append((model, constraint_name))

    messages = []
    for truncated_name, model_constraints in known_constraints.items():
        if len(model_constraints) == 1:
            continue
        _models = [f'{model._meta.app_label}.{model.__name__}' for model, _ in model_constraints]
        models_string = ', '.join(_models)
        for _model, constraint_name in model_constraints:
            messages.append(
                Error(
                    f'{_model._meta.label} constraint {constraint_name} is not unique',
                    hint='Constraint truncates to ' + truncated_name.decode('utf-8', 'replace'),
                    obj=models_string,
                    id=ID_ERROR_DB_CONSTRAINTS,
                )
            )

    return messages


def _check_explicit_table_names_on_model(model: Type[Model], enforce_lowercase: bool) -> List[CheckMessage]:
    """
    Use an ast to check if a model has the db_table meta option set.
    This is done this way because a model instance's db_table is always
    populated even if with that of the default.
    """
    messages = []
    found = None
    try:
        source = inspect.getsource(model)
    except OSError:
        # if a model class is dynamically created then we can't inspect the source code
        # (eg this happens with audit models)
        message = f"Can't get source for {model.__name__}"
        # warnings.warn(message)
        messages.append(Info(
            message,
            hint="Dynamically generated model source code can't be introspected",
            obj=model,
            id=ID_INFO_EXPLICIT_TABLE_NAME_LOWERCASE,
        ))
        return messages
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'Meta':
            for sub_node in node.body:
                if isinstance(sub_node, ast.Assign):
                    if sub_node.targets[0].id == 'db_table':
                        # in python <=3.7 it will be an ast.Str
                        # in python >=3.8 it will be an ast.Constant
                        if isinstance(sub_node.value, (ast.Constant, ast.Str)):
                            found = sub_node.value.s
                        else:
                            # If it's an expression then we don't know what it's going to evaluate it
                            # so we're just going to assume it's ok
                            found = True
                        break

                    # Skip for unmanaged models
                    elif (
                        sub_node.targets[0].id == 'managed'
                        and isinstance(sub_node.value, (ast.Constant))
                        and sub_node.value.s == False
                    ):
                        found = True
                        break
    if not found:
        messages.append(
            Error(
                'Explicit table name required',
                hint=f'Add db_table setting to {model._meta.label} model Meta',
                obj=model,
                id=ID_ERROR_EXPLICIT_TABLE_NAME,
            )
        )
    elif enforce_lowercase and hasattr(found, "islower") and not found.islower():
        messages.append(
            Error(
                'Table names must be lowercase',
                hint=f'Check db_table setting for {model._meta.label}',
                obj=model,
                id=ID_ERROR_EXPLICIT_TABLE_NAME_LOWERCASE,
            )
        )

    return messages


DEFAULT_TABLE_NAME_CHECK_IGNORE = [
    'auth',
]


class CheckExplicitTableNames:
    """
    A check for models with missing or invalid db_table settings
    """

    ignore_labels: Iterable[str]
    enforce_lowercase: bool

    def __init__(self, ignore_labels: Iterable[Union[str, Pattern]] = DEFAULT_TABLE_NAME_CHECK_IGNORE, enforce_lowercase: bool = True):
        """
        ignore_labels: ignore apps or models matching supplied labels
        enforce_lowercase: applies rule E010 which enforces table name to be all lowercase; defaults to True
        """
        self.ignore_labels = ignore_labels
        self.enforce_lowercase = enforce_lowercase

    def __call__(self, app_configs: Iterable[AppConfig], **kwargs) -> List[CheckMessage]:
        """
        Warn when models don't have Meta's db_table_name set in apps that require it.
        """
        candidate_models = find_candidate_models(app_configs, self.ignore_labels)

        messages = []
        for model in candidate_models.values():
            messages += _check_explicit_table_names_on_model(model, self.enforce_lowercase)
        return messages


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

    def _check_field_names_on_model(self, model: Type[Model]) -> List[CheckMessage]:
        """
        check whether field names on model are legit

        currently contains only one check:
        1. checks whether field name contains any number preceded by an underscore. the underscore will be lost when
           camelized then de-camelized again. Since camelize is performed automatically to/from frontend it leads to bugs.

        """

        messages = []

        for field in model._meta.fields:
            if camel_to_underscore(underscore_to_camel(field.name)) != field.name:
                hint = None
                if re.search(r'_[0-9]', field.name):
                    hint = f'Underscore before a number in {model._meta.label}.{field.name}'
                messages.append(
                    Error(
                        "Field name is not reversible with underscore_to_camel()/camel_to_underscore()",
                        hint=hint,
                        obj=model,
                        id=ID_ERROR_FIELD_NAME_NOT_CAMEL_FRIENDLY,
                    )
                )

        return messages