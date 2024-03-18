# Inspired by https://github.com/vbabiy/djangorestframework-camel-case
# (but apart from 2 regexes, completely rewritten in order to add `ignore` parameters)
from __future__ import annotations

from collections import OrderedDict
import re
from typing import Any
from typing import Callable
from typing import cast
from typing import Dict
from typing import Iterable
from typing import List
from typing import Literal
from typing import Mapping
from typing import Sequence
from typing import Tuple
from typing import TypeVar
from typing import Union

from django.core.files import File
from django.utils.functional import Promise
from typing_extensions import TypeAlias

_first_cap_re = re.compile('(.)([A-Z][a-z]+)')
_all_cap_re = re.compile('([a-z0-9])([A-Z])')
_re_underscore = re.compile(r'(?!^)(?<!_)_([^_])')

"""
a sequence of fields to ignore when camelizing
# see camelize()/underscorize()
"""
IgnoreSpecifier = Iterable[str]

# Internal structure: see _create_ignore_lookup() for usage
# Exposed only for typing purposes; treat this as an opaque type
IgnoreDict: TypeAlias = Dict[Union[str, None], Union["IgnoreDict", Literal[True]]]

_empty_dict: IgnoreDict = {} # we use this a lot in here


# a generic type that can be camelized/underscorized
CamelizeT = TypeVar('CamelizeT')


def _debug_lookup(ignore_tree: IgnoreDict, indent: int = 0) -> List[str]:
    """
    Format a tree processed by _transform_ignore() into something human-readable (for debugging/testing purposes)
    """
    x = []
    for sort_key, key, children in sorted([(key or '', key, val) for key, val in ignore_tree.items()]):
        if key is None:
            continue
        assert children is not True  # only None key should have a children value of True

        line = ' ' * 4 * indent + str(key) + ('!' if None in children else '')
        x.append(line)
        if isinstance(children, Mapping):
            x += _debug_lookup(children, indent + 1)
    return x


def _create_ignore_lookup(ignore: IgnoreSpecifier) -> IgnoreDict:
    """
    Transforms a list of field-paths-to-ignore of the following form:
    [
        'a.b',
        'a.b.c',
        'a.*.d',
        'e.*.f',
    ]

    into a more-easily traversible structure:

    {
        'a': {
            'b': {
                None: True,
                'c': { None: True}
                'd': { None: True}
            }
            '*': {
                'd': { None: True}
            }
        }
        'e': {
            '*': {
                'f': { None: True}
            }
        }
    }

    - {None: True} is used to indicate that this is a terminal expression (it makes traversing the tree simpler)
    - True is used as the wildcard index (we don't store a literal '*' in case the field value we're matching against is an actual '*')


    This allows you to determine whether a given field path is in the ignore list by checking whether a tree recurse
    ends with a True value at the None index; at each level if the next path is missing then use the '*' element if
    present


    Assumptions/Constraints:
        - All indices must be strings with a . path separator
        - Zero-length strings are not valid
        - * is a wildcard indicator
    TODO: In future if we allow pre-split paths then we might relax some of these constraints

    :param ignore: list of field paths to ignore
    :return: See above
    """

    def process_path(parts: Sequence[str], candidates: List[IgnoreDict]):
        """
        Breadth-first transform of the tree; will merge `parts` into the sub-tree(s) specified by `candidates`

        :param parts: list of field path parts (ie already split on '.') relative to candidates
        :param candidates: list of current candidate sub-trees to process
        """
        while len(parts):
            part = parts[0]
            assert part != ''

            new_candidates: List[IgnoreDict] = []

            for candidate in candidates:
                if part not in candidate:
                    candidate[part] = {}

                if len(parts) > 1:
                    if part == '*':
                        # all candidates
                        new_candidates.extend(cast(Iterable[IgnoreDict], candidate.values()))
                    else:
                        new_candidate = cast(IgnoreDict, candidate[part])
                        assert candidate[part] is not True
                        new_candidates.append(new_candidate)
                else:
                    # current element is a terminal
                    cast(IgnoreDict, candidate[part])[None] = True

            candidates = new_candidates
            parts = parts[1:]

    ignore_parts = [x.split('.') for x in ignore]
    # We need to process the wildcard parts last, so sort according to wildcard positions
    ignore_parts_keyed = [(tuple(part == '*' for part in path), path) for path in ignore_parts]
    ignore_parts_keyed.sort(key=lambda x: x[0])
    ignore_parts = [x[1] for x in ignore_parts_keyed]

    # Now do the processing
    data: IgnoreDict = {}
    for parts in ignore_parts:
        process_path(parts, [data])
    return data


def _transform_key_val(
    key: Union[str, Promise],
    value: CamelizeT,
    transform_key: Callable,
    ignore_lookup: Dict
) -> Tuple[str, CamelizeT]:
    """
    Transform a particular key/value pair
    - Will rename the key if it's not in the ignore_lookup
    - Will recursively transform the value

    :param key: key name
    :param value: data value
    :param transform_key: key transform function
    :param ignore_lookup: lookup if field name ignores (see _create_ignore_lookup)
    :return: (new_key, transformed_value)
    """
    # To make keys consistent with how we treat values force django `Promise` to a string; this means
    # lazy strings (eg. gettext_lazy) will be properly converted to camel case
    if isinstance(key, Promise):
        key = str(key)
    if key in ignore_lookup:
        ignore_lookup = ignore_lookup[key]
    elif '*' in ignore_lookup:
        ignore_lookup = ignore_lookup['*']
    else:
        ignore_lookup = _empty_dict

    if not (ignore_lookup.get(None, False) is True):
        key = transform_key(key)

    assert not isinstance(key, Promise)
    return key, _transform_data(value, transform_key, ignore_lookup)


def _transform_data(data: CamelizeT, transform_key: Callable, ignore_lookup: Dict) -> CamelizeT:

    # Mapping (dict) -- transform keys
    if isinstance(data, Mapping):
        cls = OrderedDict if isinstance(data, OrderedDict) else dict
        return cls(
            _transform_key_val(key, value, transform_key, ignore_lookup)
            for (key, value) in data.items()
        )

    # Iterable - we'll want to use iterable to cover all ... iterables, such as a list or a queryset,
    # but we'll want to ignore two common iterable types: str & bytes. We also ignore File specifically for
    # the case in djrad where it will transform incoming multipart form data from the frontend into a dict
    # containing File objects for any file fields.
    # At least for now we don't support numeric indices in ignores, so '*' is the only ignore lookup index
    # that can match a list/iterable
    # `Promise` is included here as django uses that as the base for proxy class created in lazy functions, eg.
    # gettext_lazy. Without this they are treated as an iterable.
    if isinstance(data, Iterable) and not isinstance(data, (str, bytes, File, Promise)):
        ignore_lookup = ignore_lookup.get('*', _empty_dict)
        transformed = [_transform_data(x, transform_key, ignore_lookup) for x in data]
        # this cast is not strictly true, but for our purposes an iterable => list might as well be the same type
        return cast(CamelizeT, transformed)

    # is a string/scalar/noniterable; return as-is
    # the cast is because mypy incorrectly thinks the type could have changed
    return cast(CamelizeT, data)


def underscore_to_camel(key: str) -> str:
    """
    Turn underscores into camel case

    Double underscores will be left alone

    :param key: underscore-case string
    :return: camel-case string
    """
    try:
        return re.sub(
            _re_underscore,
            lambda match: match.group()[1].upper(),
            key
        )
    except TypeError:
        # Not a string... ignore
        return key


def camelize(data: CamelizeT, ignore: IgnoreSpecifier = []) -> CamelizeT:
    """
    Recursively turn underscore-cased keys into camel-cased keys

    :param data:
    :param ignore: list of key paths to ignore; see `_creat_ignore_lookup`
    :return: structure with keys turned into camelcase
    """
    return _transform_data(data, underscore_to_camel, ignore_lookup=_create_ignore_lookup(ignore))


def camel_to_underscore(key: str) -> str:
    """
    Turn camel-cased key into underscore key

    :param key: camel-casestring
    :return: underscore-case string
    """
    try:
        s1 = _first_cap_re.sub(r'\1_\2', key)
        return _all_cap_re.sub(r'\1_\2', s1).lower()
    except TypeError:
        # Not a string... ignore
        return key


def underscoreize(data: CamelizeT, ignore: IgnoreSpecifier = []) -> CamelizeT:
    """
    Recursively turn camelcase keys into underscored keys

    :param data:
    :param ignore: list of key paths to ignore; see `_create_ignore_lookup`
    :return: structure with keys turned into camelcase
    """
    return _transform_data(data, camel_to_underscore, ignore_lookup=_create_ignore_lookup(ignore))
