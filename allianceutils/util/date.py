# IMPORTANT
# python_to_django_date_format() may be used in django settings files
# If you import django in this file that should be considered a breaking change
import re
from typing import Callable
from typing import Match
from typing import Tuple

_date_format_map = {
    '%%': '%',
    '%a': 'D',
    '%A': 'l',
    '%b': 'M',
    '%B': 'F',
    '%c': None,
    '%d': 'd',
    '%-d':'j',
    '%f': None,
    '%H': 'H',
    '%-H':'G',
    '%I': 'h',
    '%-I':'g',
    '%j': 'z',
    '%m': 'm',
    '%-m':'n',
    '%M': 'i',
    '%p': 'A',
    '%S': 's',
    '%U': '',
    '%w': 'w',
    '%W': 'W',
    '%x': None,
    '%X': None,
    '%y': 'y',
    '%Y': 'Y',
    '%z': 'O',
    '%Z': 'e',
}
_date_format_re = re.compile('|'.join(re.escape(key) for key in _date_format_map))


def _date_format_replace(x: Match) -> str:
    new_fmt = _date_format_map[x.group(0)]
    if new_fmt is None:
        raise ValueError("Python date format string {x.group(0} has no django date template equivalent")
    return new_fmt


def python_to_django_date_format(python_format: str) -> str:
    """
    Convert python date formatting string to django date formatting string
    """
    return _date_format_re.sub(_date_format_replace, python_format)
