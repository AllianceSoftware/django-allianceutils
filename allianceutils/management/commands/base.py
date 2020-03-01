from django.apps import AppConfig
from django.apps import apps
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from allianceutils.util.get_firstparty_apps import get_firstparty_apps


class OptionalAppCommand(BaseCommand):
    """
    A variant of AppCommand that takes an optional list of app labels and passes
    the corresponding app config to handle_app_config().  If no app labels are
    supplied it attempts to find all local apps by using isort's method
    of determining if a module is first party or not.
    """
    def add_arguments(self, parser):
        parser.add_argument('args', metavar='app_label', nargs='*')

    def handle(self, *app_labels, **options):
        if len(app_labels) > 0:
            try:
                app_configs = [
                    apps.get_app_config(app_label)
                    for app_label in app_labels
                ]
            except (LookupError, ImportError) as e:
                raise CommandError("%s. Are you sure your INSTALLED_APPS setting is correct?" % e)
        else:
            app_configs = get_firstparty_apps()

        output = []
        for app_config in app_configs:
            app_output = self.handle_app_config(app_config, **options)
            if app_output:
                output.append(app_output)
        return '\n'.join(output)

    def handle_app_config(self, app_config: AppConfig, **options):
        """
        Perform the command's actions for app_config, an AppConfig instance
        corresponding to an application label given on the command line.
        """
        raise NotImplementedError(
            "Subclasses of AppCommand must provide"
            "a handle_app_config() method."
        )
