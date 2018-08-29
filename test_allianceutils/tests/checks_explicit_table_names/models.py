from django.db import models


class WithoutTableName(models.Model):
    name = models.CharField(max_length=20)


class WithTableName(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        db_table = 'with_table_name'


class WithTableNameUpperCase(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        db_table = 'with_TABLE_name_UPPERCASE'
