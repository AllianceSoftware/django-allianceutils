from django import template

register = template.Library()


class DefaultValueNode(template.Node):
    def __init__(self, assignments):
        self.assignments = assignments

    def render(self, context: template.Context):
        for key, val in self.assignments.items():
            context.setdefault(key, val.resolve(context))
        return ''


@register.tag('default_value')
def do_default_value(parser: template.base.Parser, token: template.base.Token):
    """
    Sets the default value for multiple entries in the context

    For example::

        {% default_value total=expression %}

    Multiple values can be added to the context::

        {% default_value foo=1 bar=2 %}

    Note that this only takes effect in the current context scope; some tags (eg 'with') will undo this when they end
    their block

    """
    bits = token.split_contents()
    remaining_bits = bits[1:]
    assignments = template.base.token_kwargs(remaining_bits, parser)
    if not assignments:
        raise template.TemplateSyntaxError("%r expected at least one variable assignment" % bits[0])
    if remaining_bits:
        raise template.TemplateSyntaxError("%r received an invalid token: %r" % (bits[0], remaining_bits[0]))
    # nodelist = parser.parse()
    # parser.delete_first_token()
    return DefaultValueNode(assignments)
