import re
import sys

from pkg_resources import parse_version
import setuptools

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

package_name = 'allianceutils'

__version__ = str(highest_ver)
# uncomment to confirm version calculation is working
# print('%s version %s' % (package_name, __version__))
# raise SystemExit()


install_requires = [
    # remember to keep this in sync with requirements.txt if necessary
    'django >= 1.11',
    'isort == 4.3.20',
]

# setuptools only added environment markers in v20.5
if parse_version(setuptools.__version__) >= parse_version('20.3'):
    install_requires.append('typing; python_version < "3.5"')
elif sys.version_info < (3, 5):
    install_requires.append('typing')

setuptools.setup(
    name=package_name,
    version=__version__,
    author='Alliance Software',
    author_email='support@alliancesoftware.com.au',
    packages=[package_name],
    include_package_data=True,
    description='Alliance Software common utilities for django',
    # long_description=...,
    # license='??',
    url='http://gitlab.internal.alliancesoftware.com.au/alliance/alliance-django-utils',
    classifiers=[],
    download_url='http://gitlab.internal.alliancesoftware.com.au/alliance/alliance-django-utils/repository/archive.tar.gz?ref=' + __version__,
    keywords=[
        'alliance',
        'alliancesoftware',
        'django',
    ],
    install_requires=install_requires,
    extras_require={
        # keep in sync with requirements-optional.txt
        'API': ['djangorestframework'],
        'Filters': ['django-filter'],
        'Logging': ['logging_tree'],
        'Permissions': ['rules'],
    },
)
