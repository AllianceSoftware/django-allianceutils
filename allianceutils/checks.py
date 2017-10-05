from typing import Iterable
from typing import Mapping

from django.conf.urls import RegexURLResolver
from django.core.checks import Warning
from django.urls import get_resolver


def check_url_trailing_slash(expect_trailing_slash: bool, ignore_attrs: Mapping[str, Iterable[str]]={}):

    def _check_url_trailing_slash(app_configs, **kwargs):
        # We ignore app_configs; so does django core check_url_settings()
        # Consider where ROOT_URLCONF points app A urlpatterns which include() app B urlpatterns
        # which define a URL to view in app C -- which app was the one that owned the URL?
        _ignore_attrs = {
            '_regex': [
                '^$',
            ],
            'lookup_str': [
                'django.views.static.serve',
            ],
            'app_name': [
                'djdt',
            ],
        }
        _ignore_attrs.update(ignore_attrs)

        def check_resolver(resolver: RegexURLResolver, depth: int=0):
            warnings = []
            for url_pattern in resolver.url_patterns:

                # look
                if any(getattr(url_pattern, attr, None) in vals for attr, vals in _ignore_attrs.items()):
                    continue

                regex_pattern = url_pattern.regex.pattern
                if regex_pattern == '^$':
                    # empty patterns are a special case; they may be nested inside an
                    # include(), if that's the case then we don't really care whether
                    # they do or don't have a slash
                    continue

                if hasattr(url_pattern, 'url_patterns'):
                    # is a resolver, not a pattern: recurse
                    warnings.extend(check_resolver(url_pattern, depth+1))

                elif regex_pattern.endswith('/$') != expect_trailing_slash:
                        warnings.append(
                            Warning(
                                'The URL pattern {} is inconsistent with expect_trailing_slash'.format(url_pattern.describe()),
                                obj=url_pattern,
                                id='allianceutils.W004',
                            )
                        )

            return warnings

        return check_resolver(get_resolver())
    return _check_url_trailing_slash
