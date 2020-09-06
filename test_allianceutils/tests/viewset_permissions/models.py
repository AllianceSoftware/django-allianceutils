from django.db import models


class NinjaTurtleModel(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=100)
    shell_size = models.DecimalField(decimal_places=1, max_digits=5)

    class Meta:
        permissions = (
            ('can_eat_pizza', 'Can Eat Pizza'),
        )
