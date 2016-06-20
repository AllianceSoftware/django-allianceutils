
import json

from django import template
from django.utils.html import escapejs
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def script_json(value):
    """
    Serialize a python object via json in a manner safe for use in <script> tags. See http://stackoverflow.com/a/14290542

    Example:
    <script type="text/javascript">
        var myVar = {{ myVariable|script_json }};
    </script>
    """
    return mark_safe('JSON.parse("%s")' % escapejs(json.dumps(value)))
