from django.db import models


class UserManager(models.Manager):
    def get_by_natural_key(self, username):
        return self.get(username=username)


class User(models.Model):
    objects = UserManager()
    username = models.CharField(max_length=10)

    def natural_key(self):
        return (self.username,)


class Person(User):
    objects = UserManager() # type:ignore[misc]
    label = models.CharField(max_length=10)


class Customer(Person):
    objects = UserManager() # type:ignore[misc]
    num = models.IntegerField()


class Purchase(models.Model):
    customer = models.ForeignKey(to=Customer, null=False, on_delete=models.CASCADE)

    def natural_key(self):
        return (self.customer.natural_key(),)
