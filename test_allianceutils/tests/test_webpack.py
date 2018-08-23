from distutils.util import strtobool
import os
from pathlib import Path
import unittest

from django.conf import settings
from django.template import Context
from django.template import Template
from django.test import override_settings
from django.test import SimpleTestCase

# data that is in the webpack
stats_dev_root = 'http://0.0.0.0:3011/'
stats_dev = {
    'combined_js':  'combined.bundle.js',
    'cssonly_js':   'cssonly.bundle.js',
    'jsonly_js':    'jsonly.bundle.js',
}
stats_prod_root = '/static/webpack_dist/'
BUNDLE_DIR_NAME = stats_prod_root[len('/static/'):]
stats_prod = {
    'combined_css': 'combined.HASH.bundle.css',
    'cssonly_css':  'cssonly.HASH.bundle.css',
    'combined_js':  'combined.HASH.bundle.js',
    'jsonly_js':    'jsonly.HASH.bundle.js',
}

# expected output for script & link tags
script = '<script type="text/javascript" src="%s?abc123" ></script>'
script_attrs = '<script type="text/javascript" src="%s?abc123" %s></script>'
link = '<link type="text/css" href="%s?abc123" rel="stylesheet" />'


is_tox = strtobool(os.getenv('TOX', '0'))

def make_settings():
    stats_dev_path = Path(Path(__file__).parent, 'webpack-stats-dev.json')
    stats_prod_path = Path(Path(__file__).parent, 'webpack-stats-prod.json')

    assert (stats_dev_path.exists())
    assert (stats_prod_path.exists())

    webpack_loader_settings = {
        'INSTALLED_APPS': settings.INSTALLED_APPS + ('webpack_loader',),
        'WEBPACK_LOADER': {}
    }

    for mode, stats_path in (('dev', stats_dev_path), ('prod', stats_prod_path)):
        cfg = {
            'CACHE': False,
            'BUNDLE_DIR_NAME': BUNDLE_DIR_NAME,
            'STATS_FILE': str(stats_path),
        }
        webpack_loader_settings['WEBPACK_LOADER'][mode] = cfg

    return webpack_loader_settings


@override_settings(**make_settings())
class AllianceBundleTestCase(SimpleTestCase):

    def check_tag(self, config, bundle, extension, expected, attrs=''):
        tpl_str = '{{% load alliance_webpack %}}{{% render_entry_point "{}" "{}" config="{}" attrs="{}" %}}'.format(bundle, extension, config, attrs)
        output = Template(tpl_str).render(Context())
        self.assertEqual(output, expected)

    @override_settings(DEBUG=True)
    def test_dev(self):
        def url(filename_key):
            return stats_dev_root + stats_dev[filename_key]

        cfg = 'dev'
        self.check_tag(cfg, 'combined', 'js', script % url('combined_js'))
        self.check_tag(cfg, 'cssonly', 'js', script % url('cssonly_js'))
        self.check_tag(cfg, 'jsonly', 'js', script % url('jsonly_js'))
        self.check_tag(cfg, 'jsonly', 'js', script_attrs % (url('jsonly_js'), 'crossorigin'), attrs='crossorigin')

        self.check_tag(cfg, 'combined', 'css', '')
        self.check_tag(cfg, 'cssonly', 'css', '')
        self.check_tag(cfg, 'jsonly', 'css', '')

    def test_prod(self):
        def url(filename_key):
            return stats_prod_root + stats_prod[filename_key]
        cfg = 'prod'
        self.check_tag(cfg, 'combined', 'css', link % url('combined_css'))
        self.check_tag(cfg, 'cssonly',  'css', link % url('cssonly_css'))
        self.check_tag(cfg, 'jsonly',   'css', '')

        self.check_tag(cfg, 'combined', 'js', script % url('combined_js'))
        self.check_tag(cfg, 'cssonly',  'js', '')
        self.check_tag(cfg, 'jsonly',   'js', script % url('jsonly_js'))
