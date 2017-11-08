from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase


class PrintLoggingTestCase(SimpleTestCase):

    def test_print_logging(self):
        stdout = StringIO()
        call_command('print_logging', stdout=stdout)
        stdout = stdout.getvalue()

        # check a few logs that we know should be present
        self.assertIn('\n   |   o   "django.server"\n', stdout)
        self.assertIn('\n   |   o<--"django.template"\n', stdout)
        self.assertIn('\n   |   |   o<--"django.security.csrf"\n', stdout)
