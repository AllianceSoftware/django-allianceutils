from __future__ import annotations

from contextlib import nullcontext
import itertools
from typing import cast
from typing import List
from unittest.case import _AssertRaisesContext

from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from allianceutils.models import _ExtendedValidationError
from allianceutils.models import ErrorDictT
from allianceutils.models import ErrorT
from allianceutils.models import ExtendedErrorT
from allianceutils.models import raise_validation_errors


class ValidationErrorCase(SimpleTestCase):

    def assertValidationErrorMatch(self, ve: ValidationError, expected):
        """
        Validates that the contents of ve matches those in out, where out is a scalar/list/dict
        """

        # test case simplification:
        # rather than having extra logic to deal with the fact that merging A + B will
        # yield errors in a different order to B + A, we use assertCountEqual() which
        # compares in an order-independent manner
        if isinstance(expected, dict):
            self.assertTrue(hasattr(ve, 'error_dict'))
            ve_dict = {field: [e.message for e in field_errors] for field, field_errors in ve.error_dict.items()}
            self.assertCountEqual(expected, ve_dict)
            self.assertFalse(hasattr(ve, 'error_list'))
            self.assertFalse(hasattr(ve, 'message'))
        elif isinstance(expected, list):
            self.assertFalse(hasattr(ve, 'error_dict'))
            self.assertCountEqual(sorted([x.message for x in ve.error_list]), expected)
            self.assertFalse(hasattr(ve, 'message'))
        else:
            self.assertFalse(hasattr(ve, 'error_dict'))
            if expected is None:
                self.assertEqual(ve.error_list, [])
                self.assertFalse(hasattr(ve, "message"))
            else:
                self.assertEqual([x.message for x in ve.error_list], [expected])
                self.assertEqual(ve.message, expected)

    def test_is_empty(self):
        # these test cases can be passed to both a ValidationError and _ExtendedValidationError
        test_cases_vanilla: list[tuple[bool, ErrorT]] = [
            # (is_empty, message)
            (False, ''),
            (False, ['']),
            (False, 'foo'),
            (False, ['foo']),

            (True, {}),
            (False, {'my_field': []}),

            (False, cast(ErrorDictT, {'my_field': ['']})),

            (False, {'my_field': [""]}),
            (False, {'my_field': ["foo"]}),
        ]

        # these include test cases that are only valid for an _ExtendedValidationError
        test_cases_extended: list[tuple[bool, ExtendedErrorT]] = [
            # (is_empty, message)
            (True, [_ExtendedValidationError(None)]),
            (True, [_ExtendedValidationError({})]),
            (True, [_ExtendedValidationError([])]),
            (False, [_ExtendedValidationError("")]),
            (True, None),

            (False, {'my_field': ['']}),
            (False, {'my_field': [None]}),
        ]

        def assert_vanilla(is_empty: bool, message: ErrorT):
            ve = _ExtendedValidationError(ValidationError(message))
            self.assertEqual(is_empty, ve._is_empty())

            ve = _ExtendedValidationError(ValidationError(ValidationError(message)))
            self.assertEqual(is_empty, ve._is_empty())

        def assert_extended(is_empty: bool, message: ExtendedErrorT):
            ve = _ExtendedValidationError(message)
            self.assertEqual(is_empty, ve._is_empty())

            ve = _ExtendedValidationError(_ExtendedValidationError(message))
            self.assertEqual(is_empty, ve._is_empty())

            ve = _ExtendedValidationError(_ExtendedValidationError(_ExtendedValidationError(message)))
            self.assertEqual(is_empty, ve._is_empty())

        for i, (is_empty, message_vanilla) in enumerate(test_cases_vanilla):
            with self.subTest(message=message_vanilla):
                assert_vanilla(is_empty, message_vanilla)
                assert_extended(is_empty, message_vanilla)

        for i, (is_empty, message_extended) in enumerate(test_cases_extended):
            with self.subTest(message=message_extended):
                assert_extended(is_empty, message_extended)

    def test_merge(self):
        """
        Can merge ValidationErrors
        """

        # ---------------------------------------
        # these test cases are complicated enough that we have manually constructed test cases
        def build_manual_cases():
            test_cases: list[
                # (input1, input2, output)
                tuple[ExtendedErrorT, ExtendedErrorT, ExtendedErrorT]
            ] = [
                # None + scalar
                (
                    None,
                    'abc',
                    'abc',
                ),
                # None + dict
                (
                    None,
                    {'abc': ['def']},
                    {'abc': ['def']},
                ),
                (
                    None,
                    {NON_FIELD_ERRORS: 'foo'},
                    {NON_FIELD_ERRORS: ['foo']},
                ),
                # None + list
                (
                    None,
                    ["foo", "bar"],
                    ["foo", "bar"],
                ),
                # scalar + dict
                (
                    'abc',
                    {NON_FIELD_ERRORS: 'foo'},
                    {NON_FIELD_ERRORS: ['foo', 'abc']},
                ),
                # dict + dict
                (
                    {'field': 'f1', 'field2': ['f2', 'f2']},
                    {'field2': 'ab'},
                    {'field': ['f1'], 'field2': ['f2', 'f2', 'ab']},
                ),
                # list + list
                (
                    ["foo", "bar"],
                    ["baz"],
                    ["foo", "bar", "baz"],
                ),
                # list + dict
                (
                    ["foo", "bar"],
                    {"bazzy": "baz"},
                    {NON_FIELD_ERRORS: ["foo", "bar"], "bazzy": "baz"},
                ),
            ]

            # also test the inputs in reverse
            test_cases += [
                (in2, in1, out)
                for in1, in2, out
                in test_cases
            ]

            return test_cases

        # ---------------------------------------
        # for these test cases we generate an exhaustive combination of all of the test inputs
        def build_list_and_scalar_test_cases():
            list_and_scalar_test_cases = [
                # Note that `None` is not valid for a ValidationError
                # but *is* valid for an ExtendedValidationError
                None,
                '',
                'abc',
                [''],
                ['abc', ''],
            ]

            def cast_to_list(x: str | list[str]) -> list[str]:
                if isinstance(x, list):
                    return x
                return [x]

            def calculate_output(
                in1: str | list[str] | None,
                in2: str | list[str] | None,
            ) -> str | list[str] | None:
                """
                Given two 'simple' inputs (str or list[str]), return the value that if passed to
                a new ValidationError would result in the expected merger of in1 & in2

                eg
                    in1="foo", in2=["bar"] ==> ["foo", "bar"]
                    in1="foo", in2="bar" ==> ["foo", "bar"]
                    in1=None, in2="foo" ==> "foo"
                    in1=None, in2=None ==> None
                """
                if in1 is None and in2 is None:
                    return None
                if in1 is None:
                    return in2
                elif in2 is None:
                    return in1
                else:
                    return cast_to_list(in1) + cast_to_list(in2)

            test_cases: list[
                # (input1, input2, output)
                tuple[ExtendedErrorT, ExtendedErrorT, ExtendedErrorT]
            ] = []

            for in1 in list_and_scalar_test_cases:
                for in2 in list_and_scalar_test_cases:

                    # if is a list, then also create a variant where items are ValidationError instances
                    in1_candidates: list[ExtendedErrorT] = [in1]  # type:ignore[list-item]  # list invariance
                    if isinstance(in1, list):
                        in1_candidates.append([ValidationError(x) for x in in1 if x is not None])
                        in1_candidates.append([_ExtendedValidationError(x) for x in in1])

                    in2_candidates: list[ExtendedErrorT] = [in2]   # type:ignore[list-item]  # list invariance
                    if isinstance(in2, list):
                        in2_candidates.append([ValidationError(x) for x in in2 if x is not None])
                        in2_candidates.append([_ExtendedValidationError(x) for x in in2])

                    test_cases += itertools.product(
                        in1_candidates,
                        in2_candidates,
                        cast(List[ExtendedErrorT], [calculate_output(in1, in2)])
                    )

            return test_cases

        processed_test_cases = build_manual_cases()
        processed_test_cases += build_list_and_scalar_test_cases()

        # ---------------------------------------
        # now we actually run the tests
        for i, (in1, in2, out) in enumerate(processed_test_cases):
            with self.subTest(in1=in1, in2=in2):
                ve1 = _ExtendedValidationError(in1)
                ve2 = _ExtendedValidationError(in2)

                ve = ve1.merged(ve2)
                self.assertValidationErrorMatch(ve, out)
                self.assertIsNot(ve, ve1)
                self.assertIsNot(ve, ve2)

                ve = _ExtendedValidationError(ve1)
                ve.merge(ve2)
                self.assertValidationErrorMatch(ve, out)
                self.assertIsNot(ve, ve1)
                self.assertIsNot(ve, ve2)

    def test_merge_deep_copy(self):
        """
        merged validation errors should not share underlying data structures
        """
        ve1 = _ExtendedValidationError({'foo': ['bar']})
        ve2 = _ExtendedValidationError({})
        ve = ve1.merged(ve2)
        self.assertIsNot(ve.error_dict['foo'], ve1.error_dict['foo'])

    def test_add_error(self):
        ve = _ExtendedValidationError(None)
        self.assertValidationErrorMatch(ve, [])
        ve.add_error(None, 'foo')
        self.assertValidationErrorMatch(ve, 'foo')
        ve.add_error(None, ['bar', 'baz'])
        self.assertValidationErrorMatch(ve, ['foo', 'bar', 'baz'])
        ve.add_error('qq', 'rr')
        self.assertValidationErrorMatch(ve, {NON_FIELD_ERRORS: ['foo', 'bar', 'baz'], 'qq': ['rr']})
        ve.add_error('qq', ['ss'])
        self.assertValidationErrorMatch(ve, {NON_FIELD_ERRORS: ['foo', 'bar', 'baz'], 'qq': ['rr', 'ss']})

        ve = _ExtendedValidationError({'qq': 'rr'})
        self.assertValidationErrorMatch(ve, {'qq': ['rr']})
        ve.add_error('qq', 'foo')
        self.assertValidationErrorMatch(ve, {'qq': ['rr', 'foo']})
        ve.add_error(None, {'qq': 'ss'})
        self.assertValidationErrorMatch(ve, {'qq': ['rr', 'foo', 'ss']})
        ve.add_error(None, {'qq': 'tt'})
        self.assertValidationErrorMatch(ve, {'qq': ['rr', 'foo', 'ss', 'tt']})
        ve.add_error(None, 'uu')
        self.assertValidationErrorMatch(ve, {'qq': ['rr', 'foo', 'ss', 'tt'], NON_FIELD_ERRORS: ['uu']})
        ve.add_error(None, 'vv')
        self.assertValidationErrorMatch(ve, {'qq': ['rr', 'foo', 'ss', 'tt'], NON_FIELD_ERRORS: ['uu', 'vv']})

        ve = _ExtendedValidationError("mno")
        self.assertValidationErrorMatch(ve, "mno")
        ve.add_error(None, ValidationError('abc'))
        self.assertValidationErrorMatch(ve, ["mno", 'abc'])
        ve.add_error(None, ValidationError(['def']))
        self.assertValidationErrorMatch(ve, ["mno", 'abc', 'def'])
        ve.add_error(None, ValidationError({'ghi': 'jkl'}))
        self.assertValidationErrorMatch(ve, {NON_FIELD_ERRORS: ["mno", 'abc', 'def'], 'ghi': ['jkl']})

        ve = _ExtendedValidationError({"abc": "def"})
        ve.add_error(None, 'ghi')
        self.assertValidationErrorMatch(ve, {NON_FIELD_ERRORS: ["ghi"], 'abc': ['def']})

    def test_add_error_fieldname(self):
        ve = _ExtendedValidationError(None)

        with self.assertRaises(TypeError):
            ve.add_error('aaa', {'field': 'value'})

        with self.assertRaises(TypeError):
            ve.add_error('aaa', ValidationError({'field': 'value'}))

    def raise_ve(self, x):
        def f():
            raise ValidationError(x)
        return f

    def raise_nothing(self):
        pass

    def test_raise_validation_errors(self):
        """
        Basic operation of raise_validation_errors()
        """

        test_cases = (
            # wrapped_function, add_error args|None, expected ValidationError contents|None
            (
                self.raise_nothing,
                None,
                None,
            ),
            (
                self.raise_nothing,
                ('field', 'abc'),
                {'field': ['abc']},
            ),
            (
                self.raise_nothing,
                (None, ['abc']),
                ['abc'],
            ),
            (
                self.raise_ve(''),
                (None, 'abc'),
                ['', 'abc'],
            ),
            (
                self.raise_ve('abc'),
                None,
                'abc',
            ),
            (
                self.raise_ve({'field': 'abc'}),
                (None, ['def']),
                {'field': ['abc'], NON_FIELD_ERRORS: ['def']},
            ),
            (
                self.raise_ve({'field': 'abc'}),
                ('field', ['def']),
                {'field': ['abc', 'def']},
            ),
        )

        for func, add_error_args, expected in test_cases:
            raise_context: _AssertRaisesContext | nullcontext = (
                self.assertRaises(ValidationError)
                if expected is not None
                else nullcontext()
            )
            with raise_context:
                with raise_validation_errors(func) as ve:
                    if add_error_args is not None:
                        ve.add_error(*add_error_args)

            if expected is not None:
                assert isinstance(raise_context, _AssertRaisesContext)
                self.assertValidationErrorMatch(raise_context.exception, expected)

    def test_raise_validation_errors_manual(self):
        """
        If you raise an exception manually then that overrides anything in raise_context_exeption
        """
        test_wrapped_func = (
            self.raise_ve('abc'),
            self.raise_nothing,
        )
        test_exceptions = (
            ValueError('ValueError!'),
            ValidationError('ValidationError!'),
        )

        for wrapped_func in test_wrapped_func:
            for exception in test_exceptions:
                with self.assertRaises(type(exception)) as raise_context:
                    with raise_validation_errors(wrapped_func):
                        raise exception
                self.assertEqual(str(raise_context.exception), str(exception))

    def test_raise_validation_errors_no_func(self):
        """
        raise_validation_errors works without a function to wrap
        """
        with raise_validation_errors() as ve:
            pass

        with self.assertRaises(ValidationError) as raise_context:
            with raise_validation_errors() as ve:
                ve.add_error('hello', 'world')
        self.assertEqual(raise_context.exception.message_dict, {'hello': ['world']})

    def test_raise_validation_errors_non_validation_error(self):
        """
        If you raise something that's not a ValidationError in the wrapped function then
        let that exception flow up and don't enter the context block
        """
        def raise_value_error():
            raise ValueError('ValueError1!')

        x = False
        with self.assertRaises(ValueError) as raise_context:
            with raise_validation_errors(raise_value_error)  as ve:
                x = True
                raise ValueError('ValueError2!')
        self.assertFalse(x)
        self.assertEqual(str(raise_context.exception), 'ValueError1!')

    def test_capture_validation_error(self):
        """
        capture_validation_error behaviour
        """

        # normal ValidationError
        with self.assertRaises(ValidationError) as raise_context:
            with raise_validation_errors() as ve:
                with ve.capture_validation_error():
                    raise ValidationError({'foo': 'hello world'})
                # mypy doesn't realise that capture_validation_errors() should
                # swallow the exception so this code is in fact reachable
                ve.add_error('foo', 'bar')  # type:ignore[unreachable]
        self.assertEqual(raise_context.exception.message_dict, {'foo': ['hello world', 'bar']})

        # non-ValidationError raised
        with self.assertRaises(ValueError):
            with raise_validation_errors() as ve:
                with ve.capture_validation_error():
                    raise ValueError('dont catch me')

        # nothing raised
        with raise_validation_errors() as ve:
            with ve.capture_validation_error():
                pass
