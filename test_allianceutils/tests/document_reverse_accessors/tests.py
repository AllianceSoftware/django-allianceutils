from io import StringIO
import re

from django.core.management import call_command
from django.test import TestCase


class TestDocumentReverseAccessors(TestCase):
    def test_command_preview_output(self):
        out = StringIO()
        call_command('document_reverse_accessors', 'document_reverse_accessors', '-p', stdout=out)
        self.assertIn('''\
@@ -3,6 +3,8 @@

 class Person(models.Model):
     name = models.CharField(max_length=255)
+    # auditors -> test_allianceutils.tests.document_reverse_accessors.models.Task.auditor
+    # reviewers -> test_allianceutils.tests.document_reverse_accessors.models.Task.reviewer
     # task_set -> test_allianceutils.tests.document_reverse_accessors.models.Task.person


@@ -11,6 +13,7 @@
     person = models.ForeignKey('Person', on_delete=models.CASCADE)
     reviewer = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='reviewers')
     auditor = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='auditors')
+    # items -> test_allianceutils.tests.document_reverse_accessors.models.TaskItem.task


 class TaskItem(models.Model):
''', re.sub(r'^ $', '', out.getvalue(), flags=re.MULTILINE))
