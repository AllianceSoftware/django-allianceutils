from django.db import models


class ObjectCacheTestModel(models.Model):
    name = models.CharField(max_length=100)
