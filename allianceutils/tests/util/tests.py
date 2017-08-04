from django.test import TestCase

from allianceutils.util import retry_fn


class UtilTestCase(TestCase):

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
