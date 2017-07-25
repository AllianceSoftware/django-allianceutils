from __future__ import unicode_literals

from distutils.version import StrictVersion
import re

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# automatically detect the current version from the highest version in the changelog section of the README
with open('README.md', 'r') as f:
    section = None
    highest_ver = StrictVersion('0.0.0')
    for line in f.readlines():
        if re.match('^#', line):
            section = line.strip('#').strip().upper()
        if section == 'CHANGELOG' and re.match('^[ \t]*\* [0-9.]+', line):
            cur_ver = line.replace('*', ' ').strip()
            try:
                highest_ver = max(highest_ver, StrictVersion(cur_ver))
            except ValueError:
                pass

__version__ = str(highest_ver)

setup(
    name='allianceutils',
    version=__version__,
    author='Alliance Software',
    author_email='support@alliancesoftware.com.au',
    packages=['allianceutils'], # this must be the same as the name above
    include_package_data=True,
    description='Alliance Software common utilities for django',
    # long_description=...,
    # license='??',
    install_requires=[
        # remember to keep this in sync with requirements.txt if necessary
        'unipath',
    ],
    url='http://gitlab.internal.alliancesoftware.com.au/alliance/alliance-django-utils',
    classifiers=[],
    download_url='http://gitlab.internal.alliancesoftware.com.au/alliance/alliance-django-utils/repository/archive.tar.gz?ref=' + __version__,
    keywords=[
		'alliance',
		'alliancesoftware',
		'django',
	],
)
