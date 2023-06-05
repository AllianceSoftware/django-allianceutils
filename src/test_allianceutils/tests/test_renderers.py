try:
    import rest_framework
except ImportError:
    import unittest
    raise unittest.SkipTest("djangorestframework is not installed")

import json

from django.test import SimpleTestCase

from allianceutils.api.renderers import CamelCaseJSONRenderer


class TestRenderers(SimpleTestCase):
    def test_entities_renderer_renders_camel_case(self):
        renderer = CamelCaseJSONRenderer()
        result = json.loads(
            renderer.render({"data_key_foo": {"inner_key_bar": 1, "key": 2}})
        )
        self.assertIn("dataKeyFoo", result)
        self.assertIn("innerKeyBar", result["dataKeyFoo"])
        self.assertIn("key", result["dataKeyFoo"])
