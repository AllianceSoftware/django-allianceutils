from django.test import SimpleTestCase

from allianceutils.util import camel_to_underscore
from allianceutils.util import camelize
from allianceutils.util import python_to_django_date_format
from allianceutils.util import retry_fn
from allianceutils.util import underscore_to_camel
from allianceutils.util import underscoreize
from allianceutils.util.camel_case import _create_ignore_lookup
from allianceutils.util.camel_case import _debug_lookup


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
        self.assertEqual(retry_fn(fn, (ValueError, IndexError,)), 666)

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


class CamelCaseTestCase(SimpleTestCase):

    def test_camel_to_underscore(self):
        tests = {
            'aBCD': 'a_bcd',
            'HTTPFoo': 'http_foo',
            'Zoo23FooBar': 'zoo23_foo_bar',
            'AbcDEFGhiJklM': 'abc_def_ghi_jkl_m',
            'Aa': 'aa',
            '__ab__cDef__': '__ab__c_def__',

            # Numbers:
            # This behaviour may change in future
            'AZ4AYaB': 'az4_a_ya_b',  # should this be az4a_ya_b instead?
            'AZA1aB': 'aza1a_b',
            '1B': '1_b',
            'test9': 'test9',
            'test9foo': 'test9foo',
            'test9Foo': 'test9_foo',
            'test9FooBar3Baz': 'test9_foo_bar3_baz',

        }
        for test_in, test_out in tests.items():
            self.assertEqual(camel_to_underscore(test_in), test_out)

    def test_underscore_to_camel(self):
        tests = {
            '_a1_eggs': '_a1Eggs',
            'HTTP_foo': 'HTTPFoo',
            'b_a_cd_efg_h': 'bACdEfgH',
            '__foo': '__foo',
            'bar__': 'bar__',
            '__ab_cd__ef_gh__': '__abCd__efGh__',
            'a___b': 'a___b',

            # Numbers:
            # This behaviour may change in future
            # it is not possible for all of these to be reversible
            # to be safe, don't begin 'words' with numbers and things should work as expected
            '1_b': '1B',
            'a_4b': 'a4b',
            'aa_4b': 'aa4b',
            'a_a_4b': 'aA4b',
            '__ab1c_4d6h_g5_k': '__ab1c4d6hG5K',
            'test9foo': 'test9foo',
            'test_9foo': 'test9foo',
            'test9_foo': 'test9Foo',
            'test_9_foo': 'test9Foo',
        }
        for test_in, test_out in tests.items():
            self.assertEqual(underscore_to_camel(test_in), test_out)

    # def _strip_indent(self, s, indent=8):
    #     return ('\n'.join([line[indent:] for line in s.split('\n') ])).strip()

    def assertTree(self, ignore_list, expected):
        """
        Accept an ignore list (input to _create_ignore_lookup) and assert that expected output matches
        expected can be one of:
        - a nested dict - output from _create_ignore_lookup()
        - a string - output from _debug_lookup(_create_ignore_lookup())
        """
        actual = _create_ignore_lookup(ignore_list)

        if isinstance(expected, str):
            actual = _debug_lookup(actual)

            expected = expected.rstrip()
            min_indent = min((len(line) - len(line.lstrip()) for line in expected.split('\n') if line))
            expected = ('\n'.join([line[min_indent:] for line in expected.split('\n') if line]))

        self.assertEqual(actual, expected)

    def test_create_ignore_lookup_simple(self):
        tests = [
            (
                ['a'],
                {'a': {None: True} },
            ),

            (
                ['a.b', 'a.c'],
                {
                    'a': {
                        'b': {None: True},
                        'c': {None: True},
                    },
                },
            ),
        ]

        for test_in, test_out in tests:
            self.assertTree(test_in, test_out)

    def test_create_ignore_lookup_star(self):
        tests = [
            (
                [
                    'a.b',
                    'a.b.c',
                    'a.*.d',
                    'e.*.f',
                ],
                {
                    'a': {
                        'b': {
                            None: True,
                            'c': {None: True},
                            'd': {None: True}
                        },
                        '*': {
                            'd': {None: True}
                        },
                    },
                    'e': {
                        '*': {
                            'f': {None: True}
                        },
                    },
                },
            ),

            (
                ['*', 'a'],
                {
                    'a': {None: True},
                    '*': {None: True},
                },
            ),

            (
                ['a.*', 'a'],
                {
                    'a': {
                        None: True,
                        '*': {None: True},
                    },
                },
            ),

            (
                ['*', 'a', 'b.*'],
                {
                    '*': {None: True},
                    'a': {None: True},
                    'b': {
                        '*': {None: True},
                    },
                },
            ),
        ]

        for test_in, test_out in tests:
            self.assertTree(test_in, test_out)

    def test_create_ignore_lookup_debug_lookup(self):
        """
        Check that the debug function returns the right test_out
        """
        input = ['*.c', 'a', 'b.*']
        ignore_tree = {
            '*': {
                'c': {None: True},
            },
            'a': {
                None: True,
                'c': {None: True},
            },
            'b': {
                '*': {None: True},
                'c': {None: True},
            },
        }
        debug_output = '''
            *
                c!
            a!
                c!
            b
                *!
                c!
        '''
        self.assertTree(input, ignore_tree)
        self.assertTree(input, debug_output)

    def test_create_ignore_lookup_star_overlap(self):
        tests = [
            (
                ['*.c', 'a', 'b.*'],
                '''
                    *
                        c!
                    a!
                        c!
                    b
                        *!
                        c!
                ''',
            ),

            (
                ['a.b.c', 'a.b.e.d', 'a.*.c', '*.b.c', 'a.*.*.d'],
                '''
                    *
                        b
                            c!
                    a
                        *
                            *
                                d!
                            c!
                                d!
                        b
                            *
                                d!
                            c!
                                d!
                            e
                                d!
                ''',
            ),
            (
                ['a.*.c.*', 'a.b.*.d', '*.b.*.d'],
                '''
                    *
                        b
                            *
                                d!
                    a
                        *
                            c
                                *!
                        b
                            *
                                d!
                            c
                                *!
                                d!
                ''',
            ),
        ]
        for test_in, test_out in tests:
            self.assertTree(test_in, test_out)

    def test_camelize(self):
        tests = (
            (
                [1, 'a_bc_d', {'a_bc_d': {'d_ef_g': ['h_ij_k']}}],
                [],
                [1, 'a_bc_d', {'aBcD':   {'dEfG':   ['h_ij_k']}}],
            ),
            (
                [1, 'a_bc_d', {'a_bc_d': {'d_ef_g': {'h_ij_k': {'qr_s': 't_uv'}}}}, {'d_ef_g': {'h_ij_k': 4}}],
                ['*.d_ef_g', '*.*.d_ef_g.h_ij_k'],
                [1, 'a_bc_d', {'aBcD':   {'dEfG':   {'h_ij_k': {'qrS':  't_uv'}}}}, {'d_ef_g': {'hIjK':   4}}],
            ),
        )

        for test_in, ignore, test_out in tests:
            self.assertEqual(camelize(test_in, ignore), test_out)

    def test_underscorize(self):
        tests = (
            (
                [1, 'aBcD', {'aBcD': {'dEfG': ['hIjK']}}],
                [],
                [1, 'aBcD', {'a_bc_d': {'d_ef_g': ['hIjK']}}],
            ),

            (
                {'aBc': {'dEf': {'hIj': {'kLm': 'nOp'}}}},
                ['*', '*.dEf.hIj'],
                {'aBc': {'d_ef': {'hIj': {'k_lm': 'nOp'}}}},
            ),
        )

        for test_in, ignore, test_out in tests:
            self.assertEqual(underscoreize(test_in, ignore), test_out)
