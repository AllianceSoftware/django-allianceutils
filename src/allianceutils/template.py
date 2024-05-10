from collections.abc import Mapping
from collections.abc import MutableMapping
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from django.template import TemplateSyntaxError
from django.template import Variable
from django.template.base import FilterExpression
from django.template.base import NodeList
from django.template.base import Parser
from django.template.base import Token
from django.template.context import Context
from django.utils.html import format_html
from django.utils.regex_helper import _lazy_re_compile
from django.utils.safestring import SafeString


def resolve(
    value: Any,
    context: Context,
) -> Any:
    """Arguments passed in may be FilterExpression which shouldn't be resolved until render time.
    If x is a NodeList then render it
    If x is a FilterExpression then resolves it
    If x is a dict then resolves each element if it is a FilterExpression
    Otherwise value is returned as is
    """
    if isinstance(value, NodeList):
        return value.render(context)
    if isinstance(value, (Mapping, MutableMapping)):
        value = {k: v.resolve(context) if isinstance(v, FilterExpression) else v for k, v in value.items()}
    elif isinstance(value, FilterExpression):
        value = value.resolve(context)
    return value


# Regex for token keyword arguments
# Supports name=value, data-name=value, container:value=value, container:data-name=value
kwarg_re = _lazy_re_compile(r"(?:(\w+|(\w+-)+\w+|(\w+:)\w+|(\w+:)(\w+-)+\w+)=)?(.+)")


# Source: https://github.com/django/django/blob/72a86ceb33749d4fd17d3d2910e19b9d9ca1643b/django/template/base.py#L1073
# The only change is to use the regex above instead of the one in Django. This allows us to support '-' in the keyword,
# e.g. `aria-label="My Label"`, as well as ':' for namespaced attributes, e.g. `xlink:href="foo"`.
def token_kwargs(
    bits: List[str], parser: Parser, support_legacy: bool = False
) -> Dict[str, FilterExpression]:
    """
    Parse token keyword arguments and return a dictionary of the arguments
    retrieved from the ``bits`` token list.

    `bits` is a list containing the remainder of the token (split by spaces)
    that is to be checked for arguments. Valid arguments are removed from this
    list.

    `support_legacy` - if True, the legacy format ``1 as foo`` is accepted.
    Otherwise, only the standard ``foo=1`` format is allowed.

    There is no requirement for all remaining token ``bits`` to be keyword
    arguments, so return the dictionary as soon as an invalid argument format
    is reached.
    """
    if not bits:
        return {}
    match = kwarg_re.match(bits[0])
    kwarg_format = match and match[1]
    if not kwarg_format:
        if not support_legacy:
            return {}
        if len(bits) < 3 or bits[1] != "as":
            return {}

    kwargs: Dict[str, FilterExpression] = {}
    while bits:
        if kwarg_format:
            match = kwarg_re.match(bits[0])
            if not match or not match[1]:
                return kwargs
            key, _, _, _, _, value = match.groups()
            del bits[:1]
        else:
            if len(bits) < 3 or bits[1] != "as":
                return kwargs
            key, value = bits[2], bits[0]
            del bits[:3]
        kwargs[key] = parser.compile_filter(value)
        if bits and not kwarg_format:
            if bits[0] != "and":
                return kwargs
            del bits[:1]
    return kwargs


def parse_tag_arguments(
    parser: Parser, token: Token, supports_as=False
) -> Union[
    Tuple[List[Any], Dict[str, FilterExpression], Optional[str]],
    Tuple[List[FilterExpression], Dict[Any, Any], Optional[str]],
    Tuple[List[FilterExpression], Dict[str, FilterExpression], Optional[str]]
]:
    """
    use parser to parse token passed to the tag. returns args as FilterExpressions and kwargs
    this code is a stripped down version of django.template.library.parse_bits()

    eg: provided `{% tag "foo" "bar" roar="waaagh" %}`, this returns `([foo, bar], {'roar':'waaagh'}, None)`
    where foo and bar are FilterExpressions of "foo" and "bar"s that can be evaluated later based on
    context.

    If ``supports_as`` is ``True`` then will handle `{% tag "foo" "bar" as fooBar %}` and store the output of the
    tag inside the named variable (``fooBar`` in the previous example). For example, a vanilla-extract stylesheet
    could be loaded using the stylesheet tag (`{% stylesheet "./myView.css.ts" as styles %}`), and then accessed
    elsewhere in the template from the `styles` variable: `<h1 class="{{ styles.heading }}">My View</h1>`. Adding
    the tag output to the context will need to be handled by the tag class which is being used (e.g. stylesheet).

    Returns:
        3-elements tuple containing the args (a list), kwargs (a dict) and the value ``as <variable>`` if specified
        and ``supports_as`` is ``True``
    """
    tag_name, *bits = token.split_contents()
    args = []
    kwargs = {}
    target_var = None
    if len(bits) >= 2 and bits[-2] == "as":
        if not supports_as:
            raise TemplateSyntaxError(f"{tag_name} does not support the 'as' syntax")
        target_var = bits[-1]
        bits = bits[:-2]
    for bit in bits:
        # First we try to extract a potential kwarg from the bit
        kwarg = token_kwargs([bit], parser)
        if kwarg:
            # The kwarg was successfully extracted
            param, value = kwarg.popitem()
            if param in kwargs:
                # The keyword argument has already been supplied once
                raise TemplateSyntaxError(
                    "'%s' received multiple values for keyword argument '%s'" % (tag_name, param)
                )
            else:
                kwargs[str(param)] = value
        else:
            if kwargs:
                raise TemplateSyntaxError(
                    f"'{tag_name}' received some positional argument(s) after some keyword argument(s)"
                )
            else:
                # Record the positional argument
                args.append(parser.compile_filter(bit))
    return args, kwargs, target_var


def build_html_attrs(html_kwargs: Dict[str, str], prohibited_attrs: Optional[List[str]] = None) -> SafeString:
    """
    turns html_kwargs as a dict into an escaped string suitable for use as html tag attributes.
    also verifies that no prohibited_attrs are keys in html_kwargs

    eg input: {"foo": "bar", "baz": "<"}
    output: 'foo="bar" baz="&lt;"'
    """
    if prohibited_attrs:
        for k in html_kwargs.keys():
            if k in prohibited_attrs:
                raise ValueError(f"{k} shouldn't be passed to template tags -- use class attribute directly")

    # .join() doesn't know about SafeStrings so we have to build the string manually
    output = SafeString("")
    for i, (k, v) in enumerate(html_kwargs.items()):
        output += format_html('{}{}="{}"', "" if i == 0 else " ", k, v)
    return output


def is_static_expression(expr: Optional[Union[FilterExpression,str]]) -> bool:
    """Check if a given expression is static

    This can be used when writing custom template tags to determine if the value passed in is a static value, and can
    be resolved without ``context``.
    """
    if expr is None or isinstance(expr, str):
        return True
    if not isinstance(expr, FilterExpression):
        return False  # type: ignore[unreachable] # unreachable because of type, but we want to return False rather than crash if not a FilterExpression
    # the arg.var.lookups is how Variable internally determines if value is a literal. See its
    # implementation of ``resolve``.
    if  not isinstance(expr.var, Variable) or expr.var.lookups is None:
        # If it has filters then we assume it's not static
        return not expr.filters
    # There are 3 built-ins that look like vars but get resolved from a static list (see ``BaseContext``)
    return expr.var.var in ["None", "True", "False"]
