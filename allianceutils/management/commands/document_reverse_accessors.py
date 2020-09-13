import ast
import difflib
import inspect
from itertools import groupby
import re
from typing import Dict
from typing import Iterable
from typing import List
from typing import Type

from django.db.models import Field
from django.db.models import Model
from django.db.models.fields.reverse_related import ForeignObjectRel

from .base import OptionalAppCommand


class Command(OptionalAppCommand):
    COMMENT_REGEX = '^    # \w+ = \(reverse accessor\) \w+ from [\w]+\.[\w]+.[\w]+$'
    COMMENT_FORMAT = '    # {field} = (reverse accessor) {fieldtype} from {app}.{klass}.{name}\n'

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

    def determine_fields_by_model_by_file(self, models: Iterable[Type[Model]]) -> Dict[str, Dict[Model, Field]]:
        """
        Takes a list of models and returns the models & fields for each source file
        :param: models[] - look up the source file & fields for these models
        :returns: { source_file: { Model: [ Field ] } }
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
                model: model_fields[model]
                for model
                in source_file_models[source_file]
            }
            for source_file
            in source_file_models.keys()
        }
        return source_file_model_fields

    def generate_comments(self, fields_by_model_by_source_file: Dict[str, Dict[Model, Field]]) -> Dict[str, List[str]]:
        """
        takes in a dict of fields in the format returned by determine_fields_by_model_by_file
        spits out { source_file: [ lines_with_comments ] }, where lines_with_comments are consisted of
        original code (without any reverse accessor comments) + added reverse accessor comments.
        """
        output = {}
        for source_file, fields_by_model in fields_by_model_by_source_file.items():
            with open(source_file, 'r') as source_code:
                source_lines = [
                    line
                    for line
                    in source_code.readlines()
                    if not re.match(self.COMMENT_REGEX, line)
                ]
                patches = {}
                tree = ast.parse(''.join(source_lines))
                fields_by_model_names = dict([(model.__name__, model) for model in fields_by_model])

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name in fields_by_model_names:
                        model = fields_by_model_names[node.name]
                        field_names = [field.name for field in model._meta.fields]
                        ast_fields = dict([(_assign.targets[0].id, _assign.lineno) for _assign in node.body if isinstance(_assign, ast.Assign)])
                        actual_fields = set(ast_fields.keys()).intersection(set(field_names)) # do an intersection here - both ast_fields and model def fields contains some passive unwanted ones
                        if actual_fields:
                            inject_location = max([ast_fields[field] for field in actual_fields])
                        else:
                            # this model contains no active field definition at this moment; insert comments at beginning of class def
                            inject_location = node.lineno

                        patches[inject_location] = [
                            self.create_comment(field)
                            for field
                            in sorted(fields_by_model[model], key=lambda f: f.get_accessor_name())
                        ]

                # mash em up
                offset = 0
                for lineno, lines in sorted(patches.items()):
                    if source_lines[lineno+offset].strip() == '' :
                        source_lines[lineno+offset+1:lineno+offset+1] = lines
                        offset += len(lines)
                    else:
                        source_lines[lineno+offset:lineno+offset] = ['\n'] + lines
                        offset += len(lines) + 1
                output[source_file] = source_lines
        return output


    def create_comment(self, field: ForeignObjectRel) -> str:
        return self.COMMENT_FORMAT.format(
            field=field.get_accessor_name(),
            fieldtype=field.remote_field.get_internal_type(),
            app=field.remote_field.model._meta.app_label,
            klass=field.remote_field.model.__name__,
            name=field.remote_field.name,
        )

    def preview_output(self, output: Dict[str, List[str]]):
        for source_file, lines in output.items():
            with open(source_file, 'r') as source_code:
                diff = difflib.unified_diff(source_code.readlines(), lines, fromfile=source_file, tofile=source_file)
                self.stdout.writelines(diff)

    def apply_output(self, output: Dict[str, List[str]]):
        for source_file, lines in output.items():
            with open(source_file, 'w') as source_code:
                source_code.writelines(lines)
