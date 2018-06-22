import ast
import difflib
import inspect
from itertools import groupby
import re

from django.apps import apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    COMMENT_REGEX = '^    # \w+ -> [\w\.]+$'
    COMMENT_FORMAT = '    # {} -> {}.{}.{}\n'

    help = "Document reverse accessors on models."

    def add_arguments(self, parser):
        parser.add_argument('app_label', nargs='*')
        parser.add_argument('-p', '--preview', dest='preview', action='store_true', default=False, help='Preview the output in patch format')

    def handle(self, *args, **options):
        if len(options['app_label']) > 0:
            models = []
            for app_label in options['app_label']:
                app_config = apps.get_app_config(app_label)
                models += app_config.get_models()
        else:
            # todo: exclude 3rd party & core models
            models = apps.get_models()

        fields_by_model_by_source_file = self.determine_fields_by_model_by_file(models)
        output = self.generate_comments(fields_by_model_by_source_file)

        if options['preview']:
            self.preview_output(output)
        else:
            self.apply_output(output)

    def determine_fields_by_model_by_file(self, models):
        related_fields = [
            field
            for model in models
            for field in model._meta.related_objects
        ]

        fields_by_model = {
            model: list(model_fields)
            for model, model_fields in groupby(sorted(related_fields, key=lambda f: f.model.__name__), key=lambda f: f.model)
        }

        models_by_source_file = {
            source_file: list(models)
            for source_file, models in groupby(sorted(fields_by_model.keys(), key=inspect.getsourcefile), key=inspect.getsourcefile)
        }

        fields_by_model_by_source_file = {
            source_file: {
                model.__name__: fields_by_model[model]
                for model in models_by_source_file[source_file]
            }
            for source_file in models_by_source_file.keys()
        }
        return fields_by_model_by_source_file

    def generate_comments(self, fields_by_model_by_source_file):
        output = {}
        for (source_file, fields_by_model) in fields_by_model_by_source_file.items():
            with open(source_file, 'r') as source_code:
                source_lines = [
                    line
                    for line in source_code.readlines()
                    if not re.match(self.COMMENT_REGEX, line)
                ]
                patches = {}
                tree = ast.parse(''.join(source_lines))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name in fields_by_model.keys():
                        # add comments after the last known model attribute
                        model_attributes = list(filter(self.is_model_attribute, node.body))
                        if len(model_attributes) > 0:
                            lineno = model_attributes[-1].lineno
                            patches[lineno] = [
                                self.create_comment(field)
                                for field in sorted(fields_by_model[node.name], key=lambda f: f.get_accessor_name())
                            ]

                # mash em up
                for lineno, lines in patches.items():
                    source_lines[lineno:lineno] = ['\n'] + lines
                output[source_file] = source_lines
        return output

    def resolve_name_or_attr(self, func):
        if isinstance(func, ast.Attribute):
            return func.attr
        else:
            return func.id

    def is_model_attribute(self, statement):
        """
        Guess that the statement is a model field attribute by assuming so if
        it's a function call and the function ends with 'Field'
        """
        return isinstance(statement, ast.Assign) and \
            isinstance(statement.value, ast.Call) and \
            re.match(r'(ForeignKey|\w+Field)', self.resolve_name_or_attr(statement.value.func))

    def create_comment(self, field):
        return self.COMMENT_FORMAT.format(
            field.get_accessor_name(),
            field.remote_field.model.__module__,
            field.remote_field.model.__name__,
            field.remote_field.name,
        )

    def preview_output(self, output):
        for source_file, lines in output.items():
            with open(source_file, 'r') as source_code:
                diff = difflib.unified_diff(source_code.readlines(), lines, fromfile=source_file, tofile=source_file)
                self.stdout.writelines(diff)

    def apply_output(self, output):
        for source_file, lines in output.items():
            with open(source_file, 'w') as source_code:
                source_code.writelines(lines)
