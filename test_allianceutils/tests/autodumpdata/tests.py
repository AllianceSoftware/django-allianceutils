import json
import os
import shutil
import tempfile

from django.core.management import call_command
from django.test import override_settings
from django.test import TransactionTestCase

from .models import Book
from .models import Publication


class TempJSONFile(object):

    def __init__(self):
        fd, self.filename = tempfile.mkstemp(suffix=".json")
        os.close(fd)

    def __enter__(self):
        return self.filename

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            os.unlink(self.filename)
        except OSError:
            pass
        finally:
            # there might also be an .sql file
            try:
                os.unlink(self.filename.replace('.json', '.sql'))
            except OSError:
                pass


class TestAutoDumpData(TransactionTestCase):

    def setUp(self):
        Publication.objects.all().delete()
        Book.objects.all().delete()

        Publication.objects.create(isbn='9988776655')
        Book.objects.create(isbn='1234567890', is_hardcover=False)
        Book.objects.create(isbn='1122334455', is_hardcover=True)

        self.expected_json_data = [
            {"model": "autodumpdata.publication", "fields": {"isbn": "9988776655"}},
            {"model": "autodumpdata.publication", "fields": {"isbn": "1234567890"}},
            {"model": "autodumpdata.publication", "fields": {"isbn": "1122334455"}},
        ]

    def test_fixture_no_model(self):
        """
        Test autodump with no valid models
        """
        from django.core.management import call_command
        with TempJSONFile() as filename:
            call_command('autodumpdata', fixture='foobar', output=filename)
            with open(filename, 'r') as f:
                self.assertEqual('', f.read())
            self.assertEqual(os.path.exists(filename.replace('.json', '.sql')), False)

    def test_normal_filename(self):
        """
        Test autodump normal (+ SQL dump) to explicit filename
        """
        with TempJSONFile() as filename:
            call_command('autodumpdata', fixture='publication', output=filename)
    
            # check json output
            with open(filename, 'r') as f:
                data = json.load(f)
            self.assertEqual(data, self.expected_json_data)

            # check sql output
            with open(filename.replace('.json', '.sql'), 'r') as f:
                data = f.read()
            self.assertIn("REPLACE INTO `autodumpdata_publication` (`id`, `isbn`) VALUES (1,'9988776655'),(2,'1234567890'),(3", data)
            self.assertIn("REPLACE INTO `autodumpdata_book` (`publication_ptr_id`, `is_hardcover`) VALUES (2,0),(3,1);", data)

    def test_normal(self):
        """
        Test autodump normal: calculates output filename, creates fixtures directory & can be run twice
        """
        try:
            shutil.rmtree(os.path.join(os.path.dirname(__file__), 'fixtures'))
        except FileNotFoundError:
            pass
        call_command('autodumpdata', fixture='publication')
        call_command('autodumpdata', fixture='publication')

    @override_settings(SERIALIZATION_MODULES=[])
    def test_no_settings(self):
        """
        Test autodump with no SERIALIZATION_MODULES defined
        """
        with TempJSONFile() as filename:
            call_command('autodumpdata', fixture='publication', output=filename)
