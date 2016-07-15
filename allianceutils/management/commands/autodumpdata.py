import os

import django
import django.apps
from django.conf import settings
from django.core import serializers
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
import django.core.management.commands.dumpdata


def get_autodump_labels(app_config, fixture):
    """
    Takes an app config and returns an array of 'app_label.model_label' strings describing models to dump for
    a given fixture
    :param app_config: django app config
    :param fixture: fixture name
    :return: list(string)
    """
    app_models = []
    for model in app_config.get_models():
        try:
            model_fixtures = model.fixtures_autodump
        except AttributeError:
            model_fixtures = []
        if fixture in model_fixtures:
            model_name = model._meta.model_name
            app_models.append(app_config.label + '.' + model_name)
    return app_models


class Command(BaseCommand):
    """
    A lot of the code here is cut & patse from AppCommand but we want
    to allow empty app arguments (which will default to everything); we can't unset
    a class level variable (missing_args_message) without ugly code to allow this though
    """
    help = 'Alliance Software version of dumpdata with more sensible defaults.'

    def add_arguments(self, parser):
        BaseCommand.add_arguments(self, parser)

        parser.add_argument('--fixture', metavar='fixture',
            default='dev',
            help='Fixture name')
        parser.add_argument('--format', metavar='format',
            default=None,
            help='Format')
        parser.add_argument('args', metavar='app_label', nargs='*',
            help='One or more application label.')
        # parser.add_argument('args', metavar='app_label', nargs='*',
        #     help='One or more application label.')

    def handle(self, *app_labels, **options):
        from django.apps import apps

        try:
            if not app_labels:
                app_configs = django.apps.apps.get_app_configs()
            else:
                app_configs = [apps.get_app_config(app_label) for app_label in app_labels]
        except (LookupError, ImportError) as e:
            raise CommandError("%s. Are you sure your INSTALLED_APPS setting is correct?" % e)

        # no longer using yaml because of timezone errors: http://stackoverflow.com/a/13711316

        json_serializer_overriden = settings.SERIALIZATION_MODULES.get('json') == 'allianceutils.serializers.json_orminheritancefix'

        if django.get_version().split('.') < ['1', '9', '0']:
            if not json_serializer_overriden:
                message = "You need settings.SERIALIZATION_MODULES['json'] = 'allianceutils.serializers.json_orminheritancefix' or deserialization will fail where a PK is also a FK"
                self.stdout.write(self.style.WARNING(message))

        format_candidates = [options['format']]
        if json_serializer_overriden:
            format_candidates += ['json']
        else:
            format_candidates += ['json_orminheritancefix', 'json_ordered', 'json']

        for format_selected in format_candidates:
            try:
                serializers.get_serializer(format_selected)
                options['extension'] = 'json'
                break
            except serializers.SerializerDoesNotExist:
                format_selected = None
                pass

        if options['format'] is not None and format_selected != options['format']:
            message = 'Desired serialization format "%s" not available: falling back to serialization format "%s". Did you set settings.SERIALIZATION_MODULES correctly?' % (options['format'], format_selected)
            self.stdout.write(self.style.WARNING(message))
            options['extension'] = format_selected

        options['format'] = format_selected

        output = []
        for app_config in app_configs:
            app_output = self.handle_app_config(app_config, **options)
            if app_output:
                output.append(app_output)
        return '\n'.join(output)

    def handle_app_config(self, app_config, **options):
        try:
            f = app_config.module.models.get_autodump_labels
        except AttributeError:
            f = get_autodump_labels

        app_models = f(app_config, options['fixture'])
        if app_models:
            output_file = os.path.join(app_config.path, 'fixtures', options['fixture'] + '.' + options['extension'])
            call_command('dumpdata',
                *app_models,
                use_natural_foreign_keys=True,
                use_natural_primary_keys=True,
                format=options['format'],
                indent=2,
                output=output_file
            )
            self.stdout.write('Wrote to %s: %s' % (output_file, ', '.join(app_models)))
