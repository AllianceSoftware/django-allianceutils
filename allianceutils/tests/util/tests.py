from django.test import SimpleTestCase

from allianceutils.util import python_to_django_date_format
from allianceutils.util import retry_fn


class UtilTestCase(SimpleTestCase):

    def test_retry_fn(self):
        """
            Test retry_fn
        """
        def fn():
            fn.a += 1
            if fn.a <= 3:
                raise ValueError()
            if fn.a == 4:
                raise IndexError()
            return 666
        fn.a = 0
        self.assertEquals(retry_fn(fn, (ValueError, IndexError,)), 666)

        fn.a = 0
        with self.assertRaises(IndexError):
            retry_fn(fn, (ValueError, ))

        fn.a = 0
        with self.assertRaises(ValueError):
            retry_fn(fn, (ValueError, IndexError), 3)


class DateFormatTestCase(SimpleTestCase):

    def test_date_format(self):
        formats = {
            # no django equivalent:
            '%x%X': '',

            # nothing special:
            '%a%A%b%B': 'DlMF',

            # contains literal chars
            '%a99%Z': 'D99e',

            # make sure does not do recursive substitutions
            '%%c': '%c',
            '%%%ddd': '%ddd',
            '%%%p%A': '%Al',
            '%%%%': '%%',

            # Unknown % codes
            '%Q': '%Q',
        }

        for format_in, format_out in formats.items():
            self.assertEqual(python_to_django_date_format(format_in), format_out)

        format_in = ''.join(formats.keys())
        format_out = ''.join(formats.values())
        self.assertEqual(python_to_django_date_format(format_in), format_out)

        # incomplete % at the end of a string (can't include above because it gets joined and is no longer at the end)
        self.assertEqual(python_to_django_date_format('%'), '%')
