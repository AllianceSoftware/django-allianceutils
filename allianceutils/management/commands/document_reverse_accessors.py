import ast
import difflib
import inspect
from itertools import groupby
import re
from typing import Iterable
from typing import Type
from typing import Union

from django.apps import apps
from django.db.models import Model
from django.db.models.fields.reverse_related import ForeignObjectRel

from allianceutils.util.get_firstparty_apps import get_firstparty_apps
from .base import OptionalAppCommand


class Command(OptionalAppCommand):
    COMMENT_REGEX = '^    # \w+ -> [\w\.]+$'
    COMMENT_FORMAT = '    # {} = (reverse accessor) {} from {}.{} field {}\n'

    help = "Document reverse accessors on models."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('-p', '--preview', dest='preview', action='store_true', default=False, help='Preview the output in patch format')

    def handle_app_config(self, app_config, **options):
        models = [model for model in app_config.get_models()]
        source_file_model_fields = self.determine_fields_by_model_by_file(models)
        output = self.generate_comments(source_file_model_fields)

        if options['preview']:
            self.preview_output(output)
        else:
            self.apply_output(output)

    def determine_fields_by_model_by_file(self, models: Iterable[Type[Model]]):
        """
        Takes a list of models and returns the models & fields for each source file
        :param: model - look up the source file & fields for these models
        :returns: { source_file: { model_name: [ Field ] } }
        """
        related_fields = [
            field
            for model in models
            for field in model._meta.related_objects
        ]

        model_fields = {
            model: list(model_fields)
            for model, model_fields
            in groupby(sorted(related_fields, key=lambda f: f.model.__name__), key=lambda f: f.model)
        }

        source_file_models = {
            source_file: list(models)
            for source_file, models
            in groupby(sorted(model_fields.keys(), key=inspect.getsourcefile), key=inspect.getsourcefile)
        }

        source_file_model_fields = {
            source_file: {
                model.__name__: model_fields[model]
                for model
                in source_file_models[source_file]
            }
            for source_file
            in source_file_models.keys()
        }
        return source_file_model_fields

    def generate_comments(self, fields_by_model_by_source_file: dict):
        """
        takes in a dict of fields in the format returned by determine_fields_by_model_by_file
        spits out { source_file: [lines_with_comments] }
        """
        output = {}
        for (source_file, fields_by_model) in fields_by_model_by_source_file.items():
            with open(source_file, 'r') as source_code:
                source_lines = [
                    line
                    for line
                    in source_code.readlines()
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
                                for field
                                in sorted(fields_by_model[node.name], key=lambda f: f.get_accessor_name())
                            ]

                # mash em up
                offset = 0
                for lineno, lines in sorted(patches.items()):
                    source_lines[lineno+offset:lineno+offset] = ['\n'] + lines
                    offset += len(lines) + 1
                output[source_file] = source_lines
        return output

    def resolve_name_or_attr(self, func: Union[ast.Attribute, ast.Name]):
        if isinstance(func, ast.Attribute):
            return func.attr
        else:
            return func.id

    def is_model_attribute(self, statement: ast.stmt):
        """
        Guess that the statement is a model field attribute by assuming so if
        it's a function call and the function ends with 'Field'
        """
        return isinstance(statement, ast.Assign) and \
            isinstance(statement.value, ast.Call) and \
            re.match(r'(ForeignKey|\w+Field)', self.resolve_name_or_attr(statement.value.func))

    def create_comment(self, field: ForeignObjectRel):
        return self.COMMENT_FORMAT.format(
            field.get_accessor_name(),
            field.remote_field.get_internal_type(),
            field.remote_field.model.__module__,
            field.remote_field.model.__name__,
            field.remote_field.name,
        )

    def preview_output(self, output: dict):
        for source_file, lines in output.items():
            with open(source_file, 'r') as source_code:
                diff = difflib.unified_diff(source_code.readlines(), lines, fromfile=source_file, tofile=source_file)
                self.stdout.writelines(diff)

    def apply_output(self, output: dict):
        for source_file, lines in output.items():
            with open(source_file, 'w') as source_code:
                source_code.writelines(lines)
