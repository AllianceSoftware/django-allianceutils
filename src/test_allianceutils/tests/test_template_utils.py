from typing import cast

from django.template.base import Template
from django.test import SimpleTestCase

from allianceutils.template import is_static_expression
from allianceutils.templatetags.default_value import DefaultValueNode


class TestTemplateUtils(SimpleTestCase):

    def _get_as_var(self, contents: str):
        # Bit hacky, but use the default_value tag to parse the variable, which when then access from
        # ``DefaultValueNode.assignments``.
        template = Template(f'{{% load default_value %}}{{% default_value test_var={contents}  %}}')
        node: DefaultValueNode = cast(DefaultValueNode, template.compile_nodelist()[-1])
        return node.assignments['test_var']

    def test_is_static_expression_string(self):
        self.assertTrue(is_static_expression(self._get_as_var('"foo"')))

    def test_is_static_expression_bool(self):
        self.assertTrue(is_static_expression(self._get_as_var("True")))
        self.assertTrue(is_static_expression(self._get_as_var("False")))

    def test_is_static_expression_with_filter(self):
        self.assertFalse(is_static_expression(self._get_as_var("foo|add:''")))

    def test_is_static_expression_raw_string(self):
        self.assertTrue(is_static_expression("foo"))

    def test_is_static_expression_other_value(self):
        self.assertFalse(is_static_expression({}))  # type: ignore[arg-type] # just testing runtime behaviour
