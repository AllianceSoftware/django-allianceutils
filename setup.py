from __future__ import unicode_literals

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='allianceutils',
    version='0.0.1',
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
    download_url='http://gitlab.internal.alliancesoftware.com.au/alliance/alliance-django-utils/repository/archive.tar.gz?ref=0.1.1',
    keywords='alliance alliancesoftware django',
)
