from __future__ import unicode_literals

import re

from pkg_resources import parse_version

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# automatically detect the current version from the highest version in the changelog section of the README
with open('README.md', 'r') as f:
    section = None
    highest_ver = parse_version('0')
    for line in f.readlines():
        if re.match('^#', line):
            section = line.strip('#').strip().upper()
        if section == 'CHANGELOG' and re.match('^[ \t]*\* [0-9.]+(dev)?', line):
            cur_ver = line.replace('*', ' ').strip()
            try:
                cur_ver = parse_version(cur_ver)
            except ValueError:
                pass
            else:
                if cur_ver >= highest_ver:
                    highest_ver = cur_ver

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
