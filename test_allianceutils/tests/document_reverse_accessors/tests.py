from io import StringIO
import re

from django.core.management import call_command
from django.test import TestCase


class j(TestCase):
    def test_command_preview_output(self):
        out = StringIO()
        call_command('document_reverse_accessors', 'document_reverse_accessors', '-p', stdout=out)
        self.assertTrue(re.sub(r'^ $', '', out.getvalue(), flags=re.MULTILINE).endswith('''\
@@ -5,8 +5,9 @@

 class Person(models.Model):
     name = db.models.CharField(max_length=255)
-    # no_a_thing = (reverse accessor) ForeignKey from test_allianceutils.tests.document_reverse_accessors.models.NotAThing field removeme
-    # task_set = (reverse accessor) ForeignKey from test_allianceutils.tests.document_reverse_accessors.models.Task field perrrrrrrrrrrrrrson
+
+    # auditors = (reverse accessor) ForeignKey from test_allianceutils.tests.document_reverse_accessors.models.Task field auditor
+    # reviewers = (reverse accessor) ForeignKey from test_allianceutils.tests.document_reverse_accessors.models.Task field reviewer
     # task_set = (reverse accessor) ForeignKey from test_allianceutils.tests.document_reverse_accessors.models.Task field person

     non_field_attribute = True
@@ -24,6 +25,8 @@
     reviewer = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='reviewers')
     auditor = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='auditors')

+    # items = (reverse accessor) ForeignKey from test_allianceutils.tests.document_reverse_accessors.models.TaskItem field task
+

 class TaskItem(models.Model):
     name = models.CharField(max_length=255)
'''))
