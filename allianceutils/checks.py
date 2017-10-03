import re
import subprocess

from django.conf import settings
from django.conf.urls import RegexURLResolver
from django.core import urlresolvers
from django.core.checks import Error
from django.core.checks import Warning


def check_url_trailing_slash(app_configs, **kwargs):
    def check_resolver(resolver: RegexURLResolver):
        warnings = []
        for url_pattern in resolver.url_patterns:
            if hasattr(url_pattern, 'url_patterns'):
                # is a resolver, not a pattern: recurse
                warnings.extend(check_resolver(url_pattern))
            else:
                regex_pattern = url_pattern.regex.pattern

                if regex_pattern.endswith('/$') != settings.APPEND_SLASH:
                    warnings.append(
                        Warning(
                            'The URL pattern {} is inconsistent with APPEND_SLASH'.format(url_pattern.describe()),
                            obj=url_pattern,
                            id='allianceutils.W004',
                        )
                    )

        return warnings

    return check_resolver(urlresolvers.get_resolver())
