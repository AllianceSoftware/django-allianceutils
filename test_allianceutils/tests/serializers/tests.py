import os
import tempfile

from django.core import management
from django.test import TransactionTestCase

from .models import Customer
from .models import Person
from .models import Purchase
from .models import User


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


class TestNaturalKeysAndInheritance(TransactionTestCase):

    def setUp(self):
        User    .objects.create(username="tutu")
        Person  .objects.create(username="tata", label="pang")
        Customer.objects.create(username="toto", label="ping", num=23)
        c = Customer.objects.create(username="titi", label="pong", num=34)
        Purchase.objects.create(customer=c)

    def clear_tables(self):
        Purchase.objects.all().delete()
        Customer.objects.all().delete()
        Person  .objects.all().delete()
        User    .objects.all().delete()

    def dumpdata(self, args, filename,
                 natural_foreign_keys=False,
                 natural_primary_keys=False):
        management.call_command('dumpdata', *args,
                                **{'format': 'json',
                                   'output': filename,
                                   'use_natural_foreign_keys': natural_foreign_keys,
                                   'use_natural_primary_keys': natural_primary_keys})

    def readdata(self, filename):
        with open(filename, "r") as f:
            return f.read()

    def loaddata(self, filename):
        management.call_command('loaddata', filename, verbosity=0)

    def dump_and_load(self,
                      natural_foreign_keys=False,
                      natural_primary_keys=False):
        with TempJSONFile() as filename:
            # self.dumpdata(["allianceutils.tests.serializers"], filename,
            self.dumpdata(["serializers"], filename,
                          natural_foreign_keys=natural_foreign_keys,
                          natural_primary_keys=natural_primary_keys)
            self.clear_tables()
            self.loaddata(filename)
        self.assertEqual(4, len(User    .objects.all()))
        self.assertEqual(3, len(Person  .objects.all()))
        self.assertEqual(2, len(Customer.objects.all()))
        self.assertEqual(1, len(Purchase.objects.all()))

    def test_neither(self):
        """
        Test json_orminheritancefix
        """
        self.dump_and_load()

    def test_primary(self):
        """
        Test json_orminheritancefix natural PK
        """
        self.dump_and_load(natural_primary_keys=True)

    def test_foreign(self):
        """
        Test json_orminheritancefix natural FK
        """
        self.dump_and_load(natural_foreign_keys=True)

    def test_both(self):
        """
        Test json_orminheritancefix natural PK, FK
        """
        self.dump_and_load(natural_primary_keys=True,
                           natural_foreign_keys=True)
