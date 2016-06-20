import functools
from operator import __or__ as OR

from django import forms
from django.db.models import Q
import django_filters as filters


class MultipleFieldCharFilter(filters.MethodFilter):
    """
    Allows searching for a string across multiple fields
    """
    field_class = forms.CharField

    def __init__(self, names, *args, **kwargs):
        """
        :param names: list or tuple of field names to search across
        """
        # # We need to create a fake name else the base classes get upset
        # if 'name' not in kwargs:
        #     kwargs['name'] = names[0]

        super(MultipleFieldCharFilter, self).__init__(*args, **kwargs)

        self.names = names

    def filter(self, qs, value):
        value = value or ()  # Make sure we have an iterable

        if value in ([], (), {}, None, ''):
            return qs

        method = self.get_method(qs)
        lookup = self.lookup_expr
        clauses = [Q(**{'%s__%s' % (field_name, lookup): value}) for field_name in self.names]
        qs = method(functools.reduce(OR, clauses))

        if self.distinct:
            qs = qs.distinct()

        return qs
