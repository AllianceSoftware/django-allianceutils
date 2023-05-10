from io import StringIO
import re

from django.core.management import call_command
from django.test import TestCase


class j(TestCase):
    def test_command_preview_output(self):
        out = StringIO()
        call_command('document_reverse_accessors', 'document_reverse_accessors', '-p', stdout=out)
        self.assertTrue(re.sub(r'^ $', '', out.getvalue(), flags=re.MULTILINE).endswith('''\
@@ -5,10 +5,10 @@

 class Person(models.Model):
     name = db.models.CharField(max_length=255)
-    # no_a_thing = (reverse accessor) ForeignKey from document_reverse_accessors.NotAThing.removeme
-    # task_set = (reverse accessor) ForeignKey from document_reverse_accessors.Task.perrrrrrrrrrrrrrson
+
+    # auditors = (reverse accessor) ForeignKey from document_reverse_accessors.Task.auditor
+    # reviewers = (reverse accessor) ForeignKey from document_reverse_accessors.Task.reviewer
     # task_set = (reverse accessor) ForeignKey from document_reverse_accessors.Task.person
-
     non_field_attribute = True

     class Meta:
@@ -24,6 +24,7 @@
     reviewer = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='reviewers')
     auditor = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='auditors')

+    # items = (reverse accessor) ForeignKey from document_reverse_accessors.TaskItem.task

 class TaskItem(models.Model):
     name = models.CharField(max_length=255)
'''))
