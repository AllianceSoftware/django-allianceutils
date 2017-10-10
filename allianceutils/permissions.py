from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


# adapted from https://djangosnippets.org/snippets/334/
def register_custom_permissions(appname, permissions, verbosity=1):
    """
    Registers any number of custom permissions that are not related to any
    certain model (i.e. "global/app level").

    You must pass the models module of your app as the sender parameter. If you
    use "None" instead, the permissions will be duplicated for each application
    in your project.

    :param appname: name of the app the permission relates to
    :param permissions: see below
    :param verbosity: verbosity as used by django management commands (i.e. manage.py)


    Permissions is a tuple:
       (
           # codename, name
           ("can_drive", "Can drive"),
           ("can_drink", "Can drink alcohol"),
       )

    Examples:
        from myapp.mysite import models as app
        register_custom_permissions(appname, ('my_perm', 'My Permission'))

    NOTE: If your app contains any other models, then django migrations will ask whether you want to delete
    the fake content type that is created
    """

    # create a content type for the app
    ct, created = ContentType.objects.get_or_create(
        model='',
        app_label=appname,
        defaults={'name': appname},
    )
    if created and verbosity >= 2:
        print("Added custom content type '%s'" % ct)
    # create permissions
    for codename, name in permissions:
        p, created = Permission.objects.get_or_create(
            codename=codename,
            content_type__pk=ct.id,
            defaults={
                'name': name,
                'content_type': ct,
            }
        )
        if created and verbosity >= 2:
            print("Added custom permission '%s'" % p)
