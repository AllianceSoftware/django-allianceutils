from django.template import Context
from django.template import Template
from django.template.exceptions import TemplateSyntaxError
from django.test import SimpleTestCase


def collapse_lines(str):
    """ strip() each line in a string and return the remaining non-empty lines joined together"""
    return ''.join(filter(bool, (line.strip() for line in str.split('\n'))))


class DefaultValueTestCase(SimpleTestCase):
    def test_syntax_error(self):
        """ default_value syntax errors """
        with self.assertRaises(TemplateSyntaxError):
            Template('{% default_value var=bar %}')

        Template('{% load default_value %}')

        with self.assertRaises(TemplateSyntaxError):
            Template('{% load default_value %}{% default_value var= %}')

        with self.assertRaises(TemplateSyntaxError):
            Template('{% load default_value %}{% default_value var %}')

        with self.assertRaises(TemplateSyntaxError):
            Template('{% load default_value %}{% default_value "var" %}')

        with self.assertRaises(TemplateSyntaxError):
            Template('{% load default_value %}{% default_value b= a="var" %}')

        with self.assertRaises(TemplateSyntaxError):
            Template('{% load default_value %}{% default_value b="foo" a= %}')

        with self.assertRaises(TemplateSyntaxError):
            Template('{% load default_value %}{% default_value foo as bar %}')

        with self.assertRaises(TemplateSyntaxError):
            Template('{% load default_value %}{% default_value "b"=99 %}')

    def test_unused_default(self):
        """ default_value not used """
        tpl = Template('{% load default_value %}{% default_value foo="baz" %}{{ foo }}')
        self.assertEqual(tpl.render(Context({'foo': 'bar'})), 'bar')

    def test_used_default(self):
        """ default_value used """
        tpl = Template('{% load default_value %}{% default_value foo="baz" %}{{ foo }}')
        self.assertEqual(tpl.render(Context()), 'baz')

        tpl = Template('{% load default_value %}{% default_value foo=True %}{{ foo }}')
        self.assertEqual(tpl.render(Context()), 'True')

    def test_multi_var(self):
        """ default_value multiple assignment """
        tpl = Template('{% load default_value %}{% default_value foo="99" bar="123" baz="asdf" %}{{ foo }} {{ bar }} {{ baz }}')
        self.assertEqual(tpl.render(Context({'foo': 'FOO', 'baz': '99'})), 'FOO 123 99')

    def test_filters(self):
        """ default_value with filters """
        tpl = Template(
            '{% load default_value %}' +
            '{% default_value foo=bar|default:"mydefault" baz="ASdf"|lower|default:"notused1" %}' +
            '{{ foo|default:"notused2" }} {{ woo|default:"-" }} {{ baz }}')
        self.assertEqual(tpl.render(Context({'bar': False, 'woo': False})), 'mydefault - asdf')

    def test_nested_context_push(self):
        """ default_value is affected by context pushes"""
        tpl = Template(collapse_lines(
            '''
                {% load default_value %} 
                [{{ foo }} {{ bar }}]
                {% with foo=99 %}
                    [{{ foo }} {{ bar }}] 
                    {% default_value bar=11 %} 
                    [{{ foo }} {{ bar }}] 
                    {% with foo=88 %}
                        {% default_value bar=22 %} 
                        [{{ foo }} {{ bar }}]
                    {% endwith %}
                    [{{ foo }} {{ bar }}] 
                {% endwith %}
                [{{ foo }} {{ bar }}]
            '''))
        self.assertEqual(tpl.render(Context({})), '[ ][99 ][99 11][88 11][99 11][ ]')
