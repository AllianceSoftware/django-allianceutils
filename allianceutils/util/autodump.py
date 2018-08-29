"""
For internal allianceutils use only; don't use anything from this file
"""
from typing import Dict
from typing import Iterable
from typing import Optional

from django.apps import AppConfig
from django.apps import apps


class AutodumpModelFormats:
    """
    A container for formats and the model labels that should be dumped as part of that format
    """

    def __init__(self, sql: Optional[Iterable[str]]=None, json: Optional[Iterable[str]]=None):
        self.sql = sql or []
        self.json = json or []

    def all(self) -> Iterable[str]:
        """
        Get a list of models of any formats
        """
        x = set(self.json)
        x.update(self.sql)
        return list(x)

    def merged(self, x):
        """
        return a new AutodumpModelFormats that is this one merged with another AutodumpModelFormats
        """
        return AutodumpModelFormats(
            json=list(set(self.json) | set(x.json)),
            sql=list(set(self.sql) | set(x.sql)),
        )


# import from allianceutils.apps.AutodumpAppConfigMixin; it is only in this app here to work around a circular import
class AutodumpAppConfigMixin(AppConfig):

    @staticmethod
    def autodump_labels_merge(*fixtures_modelformats_list: Iterable[Dict[str, AutodumpModelFormats]]) -> Dict[str, AutodumpModelFormats]:
        """
        Merge multiple dicts of {fixture_name: AutodumpModelFormats} into a since dict
        """
        x = {}
        for fixtures_modelformats in fixtures_modelformats_list:
            for fixture, modelformats in fixtures_modelformats.items():
                x[fixture] = x.get(fixture, AutodumpModelFormats()).merged(modelformats)
        return x

    def get_autodump_labels(self) -> Dict[str, AutodumpModelFormats]:
        return get_autodump_labels_default(self)


def get_autodump_labels(app_config: AppConfig) -> Dict[str, AutodumpModelFormats]:
    """
    Takes an app config and returns a dict of {fixture_name: AutodumpModelFormats}
    describing models to dump for a each fixture

    Extending AutodumpAppConfigMixin in the app's config allows an app to
    override the set of models to dump as part of that app

    :param app_config: django app config
    """
    if isinstance(app_config, AutodumpAppConfigMixin):
        return app_config.get_autodump_labels()

    return get_autodump_labels_default(app_config)


def get_autodump_labels_default(app_config: AppConfig, add_test_model_ignores: bool=True) -> Dict[str, AutodumpModelFormats]:
    """
    Takes an app config and returns a dict of {fixture_name: AutodumpModelFormats}
    describing models to dump for a each fixture

    Only returns labels where fixtures_autodump or fixtures_autodump_sql is explicitly set on the model itself
    """
    app_models: Dict[str, AutodumpModelFormats] = {}

    for model in app_config.get_models():
        for fixture in getattr(model, 'fixtures_autodump', []):
            app_models.setdefault(fixture, AutodumpModelFormats()).json.append(model._meta.label)
        for fixture in getattr(model, 'fixtures_autodump_sql', []):
            app_models.setdefault(fixture, AutodumpModelFormats()).sql.append(model._meta.label)

    # if we don't list each model somewhere then the system check will complain that the model
    # was not in any autodump fixture, so we just create a proxy fixture called 'ignore'
    if add_test_model_ignores:
        for extra_app_label, extra_app_config in apps.app_configs.items():
            if not extra_app_label.startswith('test_'):
                continue
            for model in extra_app_config.get_models():
                app_models.setdefault('ignore', AutodumpModelFormats()).json.append(model._meta.label)

    return app_models
