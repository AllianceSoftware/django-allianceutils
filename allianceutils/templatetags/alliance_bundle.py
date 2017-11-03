from django import template
from django.conf import settings
import webpack_loader

# Handle both pre-and post 0.5 imports
try:
    from webpack_loader.utils import _get_bundle
except ImportError:
    from webpack_loader.templatetags.webpack_loader import _get_bundle

try:
    from webpack_loader.utils import get_as_tags as render_as_tags
except ImportError:
    from webpack_loader.templatetags.webpack_loader import render_as_tags


register = template.Library()


def _render_bundle(bundle_name, extension, config):
    # render_bundle() is already decorated with @register.simple_tag; if marked safe then mark_safe()
    # won't double-escape so this is ok
    return webpack_loader.templatetags.webpack_loader.render_bundle(bundle_name, extension, config)


@register.simple_tag
def alliance_bundle(bundle_name, extension='', config='DEFAULT'):
    """
    A wrapper to the webpack_bundle tag that accounts for the fact that
    - in production builds there will be separate JS + CSS files
    - in dev builds the CSS will be embedded in the webpack JS bundle

    Assumes that each JS file is paired with a CSS file.
    If you are only including JS without extracted CSS then use webpack_bundle, or include a placeholder CSS bundle
        (will just include a webpack stub; if you are using django-compress then overhead from this will be minimal)
    """
    debug = getattr(settings, 'DEBUG_WEBPACK', settings.DEBUG)
    if extension == 'css':
        if debug:
            return _render_bundle(bundle_name, 'js', config)
        else:
            return _render_bundle(bundle_name, 'css', config)
    elif extension == 'js':
        if debug:
            # do nothing; the JS will have been included with the CSS already
            return ''
        else:
            return _render_bundle(bundle_name, 'js', config)
    else:
        return _render_bundle(bundle_name, extension, config)
