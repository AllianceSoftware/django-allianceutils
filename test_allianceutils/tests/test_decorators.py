from django.test import SimpleTestCase

from allianceutils.decorators import method_cache


class DecoratorsTest(SimpleTestCase):

    def test_method_cache(self):
        class MyClass:
            def __init__(self):
                self.execution_count = 0

            @method_cache
            def my_method(self):
                self.execution_count += 1
                return self.execution_count

        obj = MyClass()
        self.assertEqual(obj.my_method(), 1)
        self.assertEqual(obj.my_method(), 1)
        self.assertEqual(obj.my_method(), 1)

        obj.my_method(_from_cache=False)
        self.assertEqual(obj.my_method(), 2)
        self.assertEqual(obj.my_method(), 2)

    def test_method_cache_validation(self):
        # extra arguments
        with self.assertRaises(AssertionError):
            class MyClass:
                @method_cache
                def my_method(self, x):
                    return 123

        # variable arguments
        with self.assertRaises(AssertionError):
            class MyClass:
                @method_cache
                def my_method(self, *args):
                    return 123

        with self.assertRaises(AssertionError):
            class MyClass:
                @method_cache
                def my_method(self, *kwargs):
                    return 123

        # classmethod
        with self.assertRaises(AssertionError):
            class MyClass:
                @method_cache
                @classmethod
                def my_method(self):
                    return 123

        # staticmethod
        with self.assertRaises(AssertionError):
            class MyClass:
                @method_cache
                @staticmethod
                def my_method(self):
                    return 123

        # regular function
        with self.assertRaises(AssertionError):
            @method_cache
            def my_method(this):
                return 123

        # we might change this in future but for now we use the "self" parameter to
        # distinguish a function from a method so the first param must be "self"
        with self.assertRaises(AssertionError):
            class MyClass:
                @method_cache
                def my_method(this):
                    return 123
