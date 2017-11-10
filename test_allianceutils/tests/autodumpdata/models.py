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
    fixtures_autodump_sql = ['publication']


# a proxy model without any fixtures_autodump
class PublicationProxy(Publication):
    class Meta:
        proxy = True


class Book(Publication):
    is_hardcover = models.BooleanField()

    fixtures_autodump = ['book']
    # implicit: inherits fixture_autodump_sql from publication

    class Meta:
        manager_inheritance_from_future = True


# a proxy model with fixtures_autodump
class BookProxy(Book):
    fixtures_autodump = ['dev']

    class Meta:
        proxy = True


# using this to test checks
class Author(models.Model):
    # a many:many field
    edited = models.ManyToManyField(to=Book, related_name='editors')

    # a many:many field with a through table
    authored = models.ManyToManyField(to=Book, through='AuthorBook', related_name='authors')

    fixtures_autodump = ['book']


class AuthorBook(models.Model):
    book = models.ForeignKey(to=Book, on_delete=models.CASCADE)
    author = models.ForeignKey(to=Author, on_delete=models.CASCADE)
    salary = models.DecimalField(decimal_places=2, max_digits=12)

    # fixtures_autodump is not present


class AbstractModel(models.Model):
    # fixtures_autodump is not present

    class Meta:
        abstract = True


class AbstractDumpModel(models.Model):
    fixtures_autodump = ['dev']

    class Meta:
        abstract = True
