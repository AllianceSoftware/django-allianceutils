import copy
import inspect

from django.conf import settings
from django.template import Context
from django.template import Template
from django.template.exceptions import TemplateSyntaxError
from django.test import override_settings
from django.test import SimpleTestCase
from unipath import Path


def strip_lines(str):
    """ strip() each line in a string"""
    return '\n'.join(line.strip() for line in str.split('\n'))


stats_dir = Path(inspect.getfile(inspect.currentframe())).parent
stats_dev = Path(stats_dir, 'webpack-stats-dev.json')
stats_prod = Path(stats_dir, 'webpack-stats-prod.json')

settings = {
    'INSTALLED_APPS': settings.INSTALLED_APPS + ('webpack_loader',),
    'WEBPACK_LOADER': {
        'DEFAULT': {
            'BUNDLE_DIR_NAME': '',
            'CACHE': False,
        },
    },
}

settings_dev = copy.deepcopy(settings)
settings_dev['DEBUG'] = True
settings_dev['WEBPACK_LOADER']['DEFAULT']['STATS_FILE'] = stats_dev

settings_prod = copy.deepcopy(settings)
settings_prod['DEBUG'] = False
settings_prod['WEBPACK_LOADER']['DEFAULT']['STATS_FILE'] = stats_prod

# data 
dev_stats = {
    'root_url':     'http://0.0.0.0:3011/',
    'combined_js':  'combined.bundle.js',
    'cssonly_js':   'cssonly.bundle.js',
    'jsonly_js':    'jsonly.bundle.js',
}
prod_stats = {
    'root_url':     '/static/dist/production/',
    'combined_css': 'combined.HASH.bundle.css',
    'cssonly_css':  'cssonly.HASH.bundle.css',
    'combined_js':  'combined.HASH.bundle.js',
    'jsonly_js':    'jsonly.HASH.bundle.js',

}

script = '<script type="text/javascript" src="%s" ></script>'
link = '<link type="text/css" href="%s" rel="stylesheet" />'


class AllianceBundleTestCase(SimpleTestCase):

    def check_tag(self, bundle, extension, expected):
        tpl = '{{% load alliance_bundle %}}{{% alliance_bundle "{}" {} %}}'.format(
            bundle,
            '"' + extension + '"' if extension else ''
        )
        output = Template(tpl).render(Context())
        self.assertEqual(output, expected)

    @override_settings(**settings_dev)
    def test_dev(self):
        def url(filename_key):
            return dev_stats['root_url'] + dev_stats[filename_key]

        self.check_tag('combined', 'css', script % url('combined_js'))
        self.check_tag('cssonly',  'css', script % url('cssonly_js'))
        self.check_tag('jsonly',   'css', script % url('jsonly_js'))

        self.check_tag('combined', 'js', '')
        self.check_tag('cssonly',  'js', '')
        self.check_tag('jsonly',   'js', '')

        self.check_tag('combined', '', script % url('combined_js'))
        self.check_tag('cssonly',  '', script % url('cssonly_js'))
        self.check_tag('jsonly',   '', script % url('jsonly_js'))

    @override_settings(**settings_prod)
    def test_dev(self):
        def url(filename_key):
            return prod_stats['root_url'] + prod_stats[filename_key]

        self.check_tag('combined', 'css', link % url('combined_css'))
        self.check_tag('cssonly',  'css', link % url('cssonly_css'))
        self.check_tag('jsonly',   'css', '')

        self.check_tag('combined', 'js', script % url('combined_js'))
        self.check_tag('cssonly',  'js', '')
        self.check_tag('jsonly',   'js', script % url('jsonly_js'))

        self.check_tag('combined', '', script % url('combined_js') + '\n' + link % url('combined_css'))
        self.check_tag('cssonly',  '', link % url('cssonly_css'))
        self.check_tag('jsonly',   '', script % url('jsonly_js'))
