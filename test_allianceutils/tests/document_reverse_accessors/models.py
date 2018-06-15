from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=255)
    # task_set -> test_allianceutils.tests.document_reverse_accessors.models.Task.person


class Task(models.Model):
    name = models.CharField(max_length=255)
    person = models.ForeignKey('Person', on_delete=models.CASCADE)
    reviewer = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='reviewers')
    auditor = models.ForeignKey('Person', on_delete=models.CASCADE, related_name='auditors')


class TaskItem(models.Model):
    name = models.CharField(max_length=255)
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='items')
