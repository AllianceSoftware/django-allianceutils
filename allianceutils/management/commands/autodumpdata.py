import errno
import os

import django
import django.apps
from django.conf import settings
from django.core import serializers
from django.core.management import call_command
from django.core.management.base import AppCommand
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


class Command(AppCommand):
    help = 'Alliance Software version of dumpdata with more sensible defaults.'

    def __init__(self, *args, **kwargs):
        self.app_counter = 0 # counter of how many apps with models we've processed
        super(Command, self).__init__(*args, **kwargs)

    def __getattribute__(self, name):
        # we need to hide the missing_args_message inherited from the parent class
        # to make the app argument(s) optional
        if name == 'missing_args_message':
            raise AttributeError()

        return super(Command, self).__getattribute__(name)

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)

        # is no public way of modifying an existing action, so we have to do this
        for action in parser._actions:
            if action.dest == u'args':
                action.nargs = '*'

        parser.add_argument('--fixture',
            metavar='fixture',
            default='dev',
            help='Fixture name')
        parser.add_argument('--format',
            metavar='format',
            default=None,
            help='Format')
        parser.add_argument('--output',
            metavar='output_filename',
            help='Output filename')
        parser.add_argument('--stdout',
            default=False,
            action='store_true',
            help='Output to stdout?')
        parser.add_argument('args',
            metavar='app_label',
            nargs='*',
            help='One or more application label.')
        # parser.add_argument('args', metavar='app_label', nargs='*',
        #     help='One or more application label.')

    def handle(self, *app_labels, **options):
        # we override options here in handle() rather than handle_app_config()
        # so that it is not executed multiple times (and you don't get repeated warnings)

        options['show_warnings'] = not options['stdout']
        options['show_info'] = not options['stdout'] and options['verbosity'] > 0

        if options['output'] and options['stdout']:
            raise CommandError('Cannot specify both --stdout and --output')

        # no longer using yaml because of timezone errors: http://stackoverflow.com/a/13711316
        try:
            json_serializer_overriden = settings.SERIALIZATION_MODULES.get('json') == 'allianceutils.serializers.json_orminheritancefix'
        except AttributeError:
            json_serializer_overriden = False

        # if django.VERSION < (1, 9):
        if not json_serializer_overriden:
            message = "You need settings.SERIALIZATION_MODULES['json'] = 'allianceutils.serializers.json_orminheritancefix' or deserialization will fail where a PK is also a FK"
            if options['show_warnings']:
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
            if options['show_warnings']:
                self.stdout.write(self.style.WARNING(message))
            options['extension'] = format_selected

        options['format'] = format_selected

        # we allow an empty list of apps to mean "all apps"
        if not app_labels:
            app_labels = [app_config.label for app_config in django.apps.apps.get_app_configs()]

        self.app_counter = 0

        return super(Command, self).handle(*app_labels, **options)

    def handle_app_config(self, app_config, **options):
        try:
            f = app_config.module.models.get_autodump_labels
        except AttributeError:
            f = get_autodump_labels

        app_models = f(app_config, options['fixture'])
        if app_models:

            self.app_counter += 1
            if (options['stdout'] or options['output']) and self.app_counter > 1:
                # we can't just count the number of app_labels because many don't have any relevant models
                raise CommandError('Cannot use --stdout or --output with multiple apps')

            if options['stdout']:
                output = None
                output_file = '[stdout]'
            elif options['output']:
                output = options['output']
                output_file = output
            else:
                fixture_dir = os.path.join(app_config.path, 'fixtures')
                output = os.path.join(fixture_dir, options['fixture'] + '.' + options['extension'])
                output_file = output

                # try to make sure the fixtures output directory exists
                # if the caller explicitly set the output file then it's up to them to do this
                try:
                    os.mkdir(fixture_dir)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise

            call_command('dumpdata',
                *app_models,
                use_natural_foreign_keys=True,
                use_natural_primary_keys=True,
                format=options['format'],
                indent=2,
                output=output
            )

            # give verbose output if not outputting to stdout
            if options['show_info']:
                self.stdout.write('Wrote to %s: %s' % (output_file, ', '.join(app_models)))
