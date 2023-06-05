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

        obj.my_method.clear_cache()
        self.assertEqual(obj.my_method(), 2)
        self.assertEqual(obj.my_method(), 2)
        obj.my_method.clear_cache()
        self.assertEqual(obj.my_method(), 3)

        self.assertEqual(obj.my_method.__name__, 'my_method')

        with self.assertRaises(AttributeError):
            # Trying to clear the class method doesn't work (we'd have
            # to keep track of every single MyClass instance to do this)
            MyClass.my_method.clear_cache()

    def test_method_cache_validation(self):
        # extra arguments
        with self.assertRaises(AssertionError):
            class MyClass:
                @method_cache
                def my_method(self, x):
                    return 123

        # variable arguments
        with self.assertRaises(AssertionError):
            class MyClass1:
                @method_cache
                def my_method(self, *args):
                    return 123

        with self.assertRaises(AssertionError):
            class MyClass2:
                @method_cache
                def my_method(self, *kwargs):
                    return 123

        # classmethod
        with self.assertRaises(AssertionError):
            class MyClass3:
                @method_cache
                @classmethod
                def my_method(self):
                    return 123

        # staticmethod
        with self.assertRaises(AssertionError):
            class MyClass4:
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
            class MyClass5:
                @method_cache
                def my_method(this):
                    return 123
