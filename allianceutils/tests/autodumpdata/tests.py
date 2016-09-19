from __future__ import unicode_literals

import json
import os
import tempfile

from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from django.test import TransactionTestCase


from .models import Publication
from .models import Book


class TempJSONFile(object):

    def __init__(self):
        fd, self.filename = tempfile.mkstemp(suffix=".json")
        os.close(fd)

    def __enter__(self):
        return self.filename

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            os.unlink(self.filename)
        except:
            pass


class TestAutoDumpData(TransactionTestCase):

    def setUp(self):
        Publication.objects.all().delete()
        Book.objects.all().delete()

        Publication.objects.create(isbn='9988776655')
        Book.objects.create(isbn='1234567890', is_hardcover=False)
        Book.objects.create(isbn='1122334455', is_hardcover=True)

    def test_fixture_no_model(self):
        """
        Test autodump with no valid models
        """
        from django.core.management import call_command
        with TempJSONFile() as filename:
            call_command('autodumpdata', fixture='foobar', output=filename)
            with open(filename, 'r') as f:
                self.assertEqual('', f.read())

    def test_normal(self):
        """
        Test autodump normal
        """
        with TempJSONFile() as filename:
            call_command('autodumpdata', fixture='publication', output=filename)
            with open(filename, 'r') as f:
                data = json.load(f)
            self.assertEqual(data, [
                {"model": "autodumpdata.publication", "fields": {"isbn": "9988776655"}},
                {"model": "autodumpdata.publication", "fields": {"isbn": "1234567890"}},
                {"model": "autodumpdata.publication", "fields": {"isbn": "1122334455"}},
            ])

    @override_settings()
    def test_no_settings(self):
        """
        Test autodump with no SERIALIZATION_MODULES defined
        """
        del settings.SERIALIZATION_MODULES
        with TempJSONFile() as filename:
            call_command('autodumpdata', fixture='publication', output=filename)
