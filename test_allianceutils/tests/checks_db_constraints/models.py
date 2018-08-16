from django.db import models


class CheckDBConstraintA(models.Model):
    bar = models.IntegerField()
    baz = models.IntegerField()

    class Meta:
        db_constraints = {
            'bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__eeeeeeeeee': 'check (bar = baz)',
            '😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___aaaa': 'check (bar = baz)',
        }


class CheckDBConstraintB(models.Model):
    bar = models.IntegerField()
    baz = models.IntegerField()

    class Meta:
        db_constraints = {
            'bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__xxxxxxxxxx': 'check (bar = baz)',
            '😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___bbbb': 'check (bar = baz)',
        }
