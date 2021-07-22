from django.db import models

try:
    import django_db_constraints
except ImportError:
    django_db_constraints = None


class CheckDBConstraintA(models.Model):
    bar = models.IntegerField()
    baz = models.IntegerField()

    class Meta:
        if django_db_constraints is not None:
            db_constraints = {
                'bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__eeeeeeeeee': 'check (bar = baz)',
                '😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___aaaa': 'check (bar = baz)',
            }

        constraints = [
            models.CheckConstraint(check=models.Q(bar=models.F('baz')), name='native_bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__eeeeeeeeee'),
            models.CheckConstraint(check=models.Q(bar=models.F('baz')), name='native_😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___aaaa'),
            models.CheckConstraint(check=models.Q(bar=models.F('baz')), name='shared_😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___aaaa'),
        ]


class CheckDBConstraintB(models.Model):
    bar = models.IntegerField()
    baz = models.IntegerField()

    class Meta:
        if django_db_constraints is not None:
            db_constraints = {
                'bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__xxxxxxxxxx': 'check (bar = baz)',
                '😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___bbbb': 'check (bar = baz)',
                'shared_😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___bbbb': 'check (bar = baz)',
            }

        constraints = [
            models.CheckConstraint(check=models.Q(bar=models.F('baz')), name='native_bar_equal_baz__aaaaaaaaaa__bbbbbbbbbb__cccccccccc__dddddddddd__xxxxxxxxxx'),
            models.CheckConstraint(check=models.Q(bar=models.F('baz')), name='native_😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀___bbbb'),
        ]
