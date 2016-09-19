from django.db import models


class PublicationManager(models.Manager):
    def get_by_natural_key(self, isbn):
        return self.get(isbn=isbn)


class Publication(models.Model):
    objects = PublicationManager()
    isbn = models.CharField(max_length=30)

    def natural_key(self):
        return (self.isbn,)

    fixtures_autodump = ['publication']


class Book(Publication):
    is_hardcover = models.BooleanField()

    fixtures_autodump = ['book']
