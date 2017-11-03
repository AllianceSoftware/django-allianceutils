from distutils.util import strtobool
import os
import random
import unittest

from django.conf import settings
from django.template import Context
from django.template import Template
from django.test import override_settings
from django.test import SimpleTestCase
from unipath import Path

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
    'combined_css': ['combined.HASH.bundle.css', '507d922378ec', 0],    # (filename, hash, timestamp)
    'cssonly_css':  ['cssonly.HASH.bundle.css',  '313cbcde517d', 0],    # timestamps are filled in in setUp()
    'combined_js':  ['combined.HASH.bundle.js',  '2e326e858b89', 0],
    'jsonly_js':    ['jsonly.HASH.bundle.js',    '6bba3662f619', 0],
}

# expected output for script & link tags
script = '<script type="text/javascript" src="%s" ></script>'
link = '<link type="text/css" href="%s" rel="stylesheet" />'


# webpack_loader caches the settings in the webpack_loader.config module so overriding settings has no effect
# instead we have to create many webpack loader configs
def cfg_key(mode, loader):
    return '%s-%s' % (mode, loader)

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

    loaders = (
        '',
        'allianceutils.webpack.TimestampWebpackLoader',
        'allianceutils.webpack.ContentHashWebpackLoader',
    )
    for loader in loaders:
        for mode, stats_path in (('dev', stats_dev_path), ('prod', stats_prod_path)):
            cfg = {
                'CACHE': False,
                'BUNDLE_DIR_NAME': BUNDLE_DIR_NAME,
                'STATS_FILE': stats_path,
            }
            if loader:
                cfg['LOADER_CLASS'] = loader
            webpack_loader_settings['WEBPACK_LOADER'][cfg_key(mode, loader)] = cfg

    return webpack_loader_settings


@override_settings(**make_settings())
class AllianceBundleTestCase(SimpleTestCase):

    def setUp(self):
        # randomize the timestamps on the production assets
        for bundle_ext, details in stats_prod.items():
            path = Path(settings.STATIC_ROOT, BUNDLE_DIR_NAME, details[0])
            assert path.exists()
            t = random.randint(0, 60 * 60 * 24 * 365 * 20)
            try:
                path.set_times(mtime=t)
                details[2] = t
            except PermissionError:
                details[2] = path.mtime()


    def check_tag(self, config, bundle, extension, expected):
        tpl_str = '{{% load alliance_bundle %}}{{% alliance_bundle "{}" "{}" "{}" %}}'.format(bundle, extension, config)
        output = Template(tpl_str).render(Context())
        self.assertEqual(output, expected)

    def _test_dev_loader(self, loader):
        if is_tox and loader:
            self.skipTest("tox doesn't use github dependencies correctly; reenable when webpack_loader PR is accepted")
        def url(filename_key):
            return stats_dev_root + stats_dev[filename_key]

        cfg = cfg_key('dev', loader)
        self.check_tag(cfg, 'combined', 'css', script % url('combined_js'))
        self.check_tag(cfg, 'cssonly', 'css', script % url('cssonly_js'))
        self.check_tag(cfg, 'jsonly', 'css', script % url('jsonly_js'))

        self.check_tag(cfg, 'combined', 'js', '')
        self.check_tag(cfg, 'cssonly', 'js', '')
        self.check_tag(cfg, 'jsonly', 'js', '')

        self.check_tag(cfg, 'combined', '', script % url('combined_js'))
        self.check_tag(cfg, 'cssonly', '', script % url('cssonly_js'))
        self.check_tag(cfg, 'jsonly', '', script % url('jsonly_js'))

    @override_settings(DEBUG=True)
    def test_dev(self):
        self._test_dev_loader(loader='')

    @override_settings(DEBUG=True)
    def test_dev_timestamp(self):
        self._test_dev_loader(loader='allianceutils.webpack.TimestampWebpackLoader')

    @override_settings(DEBUG=True)
    def test_dev_contenthash(self):
        self._test_dev_loader(loader='allianceutils.webpack.ContentHashWebpackLoader')

    def url_prod(self, filename_key):
        return stats_prod_root + stats_prod[filename_key][0]

    def _test_prod_loader(self, loader, url):
        if is_tox and loader:
            self.skipTest("tox doesn't use github dependencies correctly; reenable when webpack_loader PR is accepted")
        cfg = cfg_key('prod', loader)
        self.check_tag(cfg, 'combined', 'css', link % url('combined_css'))
        self.check_tag(cfg, 'cssonly',  'css', link % url('cssonly_css'))
        self.check_tag(cfg, 'jsonly',   'css', '')

        self.check_tag(cfg, 'combined', 'js', script % url('combined_js'))
        self.check_tag(cfg, 'cssonly',  'js', '')
        self.check_tag(cfg, 'jsonly',   'js', script % url('jsonly_js'))

        self.check_tag(cfg, 'combined', '', script % url('combined_js') + '\n' + link % url('combined_css'))
        self.check_tag(cfg, 'cssonly',  '', link % url('cssonly_css'))
        self.check_tag(cfg, 'jsonly',   '', script % url('jsonly_js'))

    def test_prod(self):
        self._test_prod_loader(loader='', url=self.url_prod)

    def test_prod_timestamp(self):
        self._test_prod_loader(
            loader='allianceutils.webpack.TimestampWebpackLoader',
            url=lambda filename_key: self.url_prod(filename_key) + '?ts=%.1f' % stats_prod[filename_key][2]
        )

    def test_prod_contenthash(self):
        self._test_prod_loader(
            loader='allianceutils.webpack.ContentHashWebpackLoader',
            url=lambda filename_key: self.url_prod(filename_key) + '?hash=' + stats_prod[filename_key][1]
        )
