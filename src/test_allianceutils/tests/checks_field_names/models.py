from django.db import models


class NameWithGenericUnderscore(models.Model):
    first_name = models.CharField(max_length=20)

    class Meta:
        db_table = 'field_name1'


class NameWithGenericNumber(models.Model):
    name1 = models.CharField(max_length=20)

    class Meta:
        db_table = 'field_name2'


class NameWithUnderscoreRightBeforeNumber(models.Model):
    name_1 = models.CharField(max_length=20)

    class Meta:
        db_table = 'field_name3'


class NameWithUnderscoreNumberInMiddle(models.Model):
    name_complex_1_field = models.CharField(max_length=20)

    class Meta:
        db_table = 'field_name4'


class NameWithUnderscoreNumberInMiddleAcceptable(models.Model):
    name_complex1_field = models.CharField(max_length=20)

    class Meta:
        db_table = 'field_name5'
