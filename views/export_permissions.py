import csv

from django.contrib.admin.views.decorators import user_passes_test
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.http import HttpResponse


@user_passes_test(lambda user: user.is_superuser)
def permissions(request):
    """
    Download a CSV of all of the available permissions
    :param request:
    :return: HttpResponse
    """
    permissions = Permission.objects.all().order_by('codename')

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="permissions.csv"'

    writer = csv.writer(response)

    writer.writerow(['Code', 'Name'])

    for permission in permissions:
        writer.writerow([permission.codename, permission.name])

    return response


@user_passes_test(lambda user: user.is_superuser)
def group_permissions(request):
    """
    Download a CSV of the permissions associated with each group
    :param request:
    :return: HttpResponse
    """
    groups = Group.objects.all().prefetch_related('permissions')

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="group_permissions.csv"'

    writer = csv.writer(response)

    writer.writerow(['Group', 'Permission Code', 'Permission Name'])

    for group in groups:
        for permission in group.permissions.all():
            writer.writerow([group.name, permission.codename, permission.name])

    return response
