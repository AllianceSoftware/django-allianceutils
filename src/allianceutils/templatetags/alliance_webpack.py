from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from ..webpack import get_chunk_tags
from ..webpack import WebpackEntryPointLoader

register = template.Library()


@register.simple_tag
def render_entry_point(entry_point_name:str, resource_type:str, attrs:str='', config:str='DEFAULT'):
    """
    For a specified entry point render HTML tags to embed all associated resource bundles limited to
    specified resource type (eg. 'js', 'css').

    :param entry_point_name: Name of the entry point. This should match one of the entries to 'entry' in the webpack config.
    :param resource_type: Currently supports 'js' or 'css'
    :param attrs: Optional attributes to pass through to the underlying HTML tag (eg. 'crossorigin')
    :param config: Config identifier to use. Maps to a key in WEBPACK_LOADER settings.


    Example:
    
        {% render_entry_point 'app' 'js' attrs="crossorigin" %}

          <script type="text/javascript" src="http://whatever/runtime.bundle.js?e2b781da02d36dad3aff" crossorigin></script>
          <script type="text/javascript" src="http://whatever/vendor.bundle.js?774c52f57ce30a5e1382" crossorigin></script>
          <script type="text/javascript" src="http://whatever/common.bundle.js?639269b921c8cf869c5f" crossorigin></script>
          <script type="text/javascript" src="http://whatever/app.bundle.js?806fc65dbad8a4dbb1cc" crossorigin></script>
        
        {% render_entry_point 'app' 'css' %}
          <link type="text/css" href="http://whatever/common.bundle.css?e2b781da02d36dad3aff" rel="stylesheet"></link>
          <link type="text/css" href="http://whatever/app.bundle.css?e2b781da02d36dad3aff" rel="stylesheet"></link>

    """
    loader = WebpackEntryPointLoader(settings.WEBPACK_LOADER[config])
    tags = get_chunk_tags(loader.get_chunks_for_entry_point(entry_point_name, resource_type), attrs)
    return mark_safe('\n'.join(tags))
