from contextlib import ExitStack as nullcontext
import itertools

from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from allianceutils.models import _ExtendedValidationError
from allianceutils.models import _NO_VALIDATION_ERROR
from allianceutils.models import raise_validation_errors


class ValidationErrorCase(SimpleTestCase):

    def assertValidationErrorMatch(self, ve: ValidationError, out):
        """
        Validates that the contents of ve matches those in out, where out is a scalar/list/dict
        """
        if isinstance(out, dict):
            self.assertTrue(hasattr(ve, 'error_dict'))
            ve_dict = {field: [e.message for e in field_errors] for field, field_errors in ve.error_dict.items()}
            self.assertEqual(out, ve_dict)
            self.assertFalse(hasattr(ve, 'error_list'))
            self.assertFalse(hasattr(ve, 'message'))
        elif isinstance(out, list):
            self.assertFalse(hasattr(ve, 'error_dict'))
            self.assertEqual([x.message for x in ve.error_list], out)
            self.assertFalse(hasattr(ve, 'message'))
        else:
            self.assertFalse(hasattr(ve, 'error_dict'))
            self.assertEqual([x.message for x in ve.error_list], [out])
            self.assertEqual(ve.message, out)

    def test_is_empty(self):
        test_cases = (
            # (is_empty, message)
            (False, None),
            (False, ''),
            (False, ['']),
            (False, [ValidationError(None)]),
            (False, [ValidationError('')]),
            (False, {}),
            (False, {'my_field': []}),
            (False, {'my_field': ['']}),
            (False, {'my_field': [None]}),
            (False, 'foo'),
            (False, ['foo']),
            (True, _NO_VALIDATION_ERROR),
        )

        for i, (is_empty, message) in enumerate(test_cases):
            ve = _ExtendedValidationError(message)
            self.assertEqual(is_empty, ve._is_empty(), 'test case failed: %s' % repr(message))

            ve = _ExtendedValidationError(ValidationError(message))
            self.assertEqual(is_empty, ve._is_empty(), 'test case failed: %s' % repr(message))

            ve = _ExtendedValidationError(_ExtendedValidationError(message))
            self.assertEqual(is_empty, ve._is_empty(), 'test case failed: %s' % repr(message))

            ve = _ExtendedValidationError(ValidationError(ValidationError(message)))
            self.assertEqual(is_empty, ve._is_empty(), 'test case failed: %s' % repr(message))

            ve = _ExtendedValidationError(_ExtendedValidationError(_ExtendedValidationError(message)))
            self.assertEqual(is_empty, ve._is_empty(), 'test case failed: %s' % repr(message))

    def test_merge(self):

        def cast_to_list(x):
            if isinstance(x, list):
                return x
            return [x]

        # we test each combination of these test inputs
        list_scalar_test_cases = [
            _NO_VALIDATION_ERROR,
            None,
            '',
            'abc',
            [None],
            [''],
            ['abc', None, ''],
        ]

        def calculate_output(in1, in2):
            if in1 is _NO_VALIDATION_ERROR:
                return in2
            elif in2 is _NO_VALIDATION_ERROR:
                return in1
            else:
                return cast_to_list(in1) + cast_to_list(in2)

        # these ones are complicated enough that if we try to automate it we're just
        # reimplementing the code we're testing, so we create manual test cases
        processed_test_cases = [
            # (input1, input2, output)
            (
                None,
                {'field': 'foo'}, {'field': ['foo'],
                NON_FIELD_ERRORS: [None]},
            ),
            (
                None,
                {NON_FIELD_ERRORS: 'foo'},
                {NON_FIELD_ERRORS: [None, 'foo']},
            ),
            (
                {NON_FIELD_ERRORS: 'foo'},
                'abc',
                {NON_FIELD_ERRORS: ['foo', 'abc']},
            ),
            (
                {'field': 'f1', 'field2': ['f2', 'f2']},
                {'field2': 'ab'},
                {'field': ['f1'], 'field2': ['f2', 'f2', 'ab']},
            ),
            (
                _NO_VALIDATION_ERROR,
                'abc',
                'abc',
            ),
            (
                ['abc'],
                _NO_VALIDATION_ERROR,
                ['abc'],
            ),
            (
                {'abc': 'def'},
                _NO_VALIDATION_ERROR,
                {'abc': ['def']},
            ),
            (
                _NO_VALIDATION_ERROR,
                {'abc': ['def']},
                {'abc': ['def']},
            ),
        ]

        for in1 in list_scalar_test_cases:
            for in2 in list_scalar_test_cases:

                # if is a list, then also create a variant where items are ValidationError instances
                in1_candidates = [in1]
                if isinstance(in1, list):
                    in1_candidates.append([ValidationError(x) for x in in1])

                in2_candidates = [in2]
                if isinstance(in2, list):
                    in2_candidates.append([ValidationError(x) for x in in2])

                processed_test_cases.extend(itertools.product(in1_candidates, in2_candidates, [calculate_output(in1, in2)]))
                processed_test_cases.extend(itertools.product(in2_candidates, in1_candidates, [calculate_output(in2, in1)]))

        for i, (in1, in2, out) in enumerate(processed_test_cases):
            ve1 = _ExtendedValidationError(in1)
            ve2 = _ExtendedValidationError(in2)

            ve = ve1.merge(ve2)
            self.assertValidationErrorMatch(ve, out)
            self.assertIsNot(ve, ve1)
            self.assertIsNot(ve, ve2)

    def test_add_error(self):
        ve = _ExtendedValidationError(None)
        self.assertValidationErrorMatch(ve, None)
        ve.add_error(None, 'foo')
        self.assertValidationErrorMatch(ve, [None, 'foo'])
        ve.add_error(None, ['bar', 'baz'])
        self.assertValidationErrorMatch(ve, [None, 'foo', 'bar', 'baz'])
        ve.add_error('qq', 'rr')
        self.assertValidationErrorMatch(ve, {NON_FIELD_ERRORS: [None, 'foo', 'bar', 'baz'], 'qq': ['rr']})
        ve.add_error('qq', ['ss'])
        self.assertValidationErrorMatch(ve, {NON_FIELD_ERRORS: [None, 'foo', 'bar', 'baz'], 'qq': ['rr', 'ss']})

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

        ve = _ExtendedValidationError(_NO_VALIDATION_ERROR)
        self.assertValidationErrorMatch(ve, _NO_VALIDATION_ERROR)
        ve.add_error(None, ValidationError('abc'))
        self.assertValidationErrorMatch(ve, 'abc')
        ve.add_error(None, ValidationError(['def']))
        self.assertValidationErrorMatch(ve, ['abc', 'def'])
        ve.add_error(None, ValidationError({'ghi': 'jkl'}))
        self.assertValidationErrorMatch(ve, {NON_FIELD_ERRORS: ['abc', 'def'], 'ghi': ['jkl']})

        ve = _ExtendedValidationError(_NO_VALIDATION_ERROR)
        ve.add_error('abc', 'def')
        self.assertValidationErrorMatch(ve, {'abc': ['def']})

    def test_add_error_fieldname(self):
        ve = _ExtendedValidationError(_NO_VALIDATION_ERROR)

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
            raise_context = self.assertRaises(ValidationError) if expected is not None else nullcontext()
            with raise_context:
                with raise_validation_errors(func) as ve:
                    if add_error_args is not None:
                        ve.add_error(*add_error_args)

            if expected is not None:
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
