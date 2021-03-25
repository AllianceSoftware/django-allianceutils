from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.permissions import BasePermission


class SimpleDjangoObjectPermissions(BasePermission):
    """
    Differs from just using DjangoObjectPermissions because it
    - does not require a queryset
    - uses a single permission for all request methods

    Note the DRF documentation:
    http://www.django-rest-framework.org/api-guide/permissions/#object-level-permissions
    get_object() is only required if you want to implement object-level permissions

    Also note that if you override get_object() then you need to manually invoke
    self.check_object_permissions(self.request, obj)
    """
    def has_permission(self, request, view):
        return request.user.has_perm(view.permission_required)

    def has_object_permission(self, request, view, obj):
        # Note: this assertion may fail with django_rules as it will happily try to check the same predicate regardless
        # of whether obj is supplied or not, meaning that both calls below will return True.
        has_perm_global = request.user.has_perm(view.permission_required)
        has_perm_obj = request.user.has_perm(view.permission_required, obj)
        assert not (has_perm_global and has_perm_obj), (
            "Object level and global permissions shouldn't both return True. "
            "This may indicate a potential security issue with your permissions."
        )
        return has_perm_global or has_perm_obj


class GenericDjangoViewsetPermissions(BasePermission):
    """
    Map viewset actions to Django permissions.
    You may subclass this class, and provide an actions_to_perms_map attribute,
    which will override the default value for any keys present. That is, if
    you specify, for instance,
        actions_to_perms_map = {
            'create': []
        }
    then no permissions will be required for the create action, but permissions
    for other actions will remain unchanged.
    """

    # Maps actions to required permission strings. *All* strings must be present
    # to allow the action.
    default_actions_to_perms_map = {
        'list':     ['%(app_label)s.view_%(model_name)s'],
        'retrieve': ['%(app_label)s.view_%(model_name)s'],
        'create':   ['%(app_label)s.add_%(model_name)s'],
        'update':   ['%(app_label)s.change_%(model_name)s'],
        'partial_update': ['%(app_label)s.change_%(model_name)s'],
        'destroy':  ['%(app_label)s.delete_%(model_name)s'],
    }

    # Default (undecorated) routes that should not perform an object
    # permission check [since get_object() makes no sense].
    default_list_routes = (
        'list',
        'create',
    )

    def __init__(self):
        self._saved_actions_to_perms_map = None

    def get_model(self, view):
        """Get the model to use for the permission check.

        By default does the following:

        - If `view` has `get_permission_model` defined it will call that
        - Otherwise will call `view.get_queryset()` and use the model from the returned queryset

        Can be overridden in cases where `get_queryset` or `get_permission_model` is not defined or permission check is
        done against a different model.
        """
        if hasattr(view, 'get_permission_model'):
            return view.get_permission_model()
        return view.get_queryset().model

    def get_actions_to_perms_map(self):
        """
        Merge the default actions to perms map with the class overrides & return
        Will cache results
        """
        if self._saved_actions_to_perms_map is None:
            self._saved_actions_to_perms_map = self.default_actions_to_perms_map.copy()
            self._saved_actions_to_perms_map.update(getattr(self, 'actions_to_perms_map', {}))

        return self._saved_actions_to_perms_map

    def get_permissions_for_action(self, action, view):
        """Given a model and an action, return the list of permission
        codes that the user is required to have."""

        model_cls = self.get_model(view)
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name,
        }
        perms_map = self.get_actions_to_perms_map()
        try:
            return [perm % kwargs for perm in perms_map[action]]
        except KeyError:
            raise ImproperlyConfigured('Missing GenericDjangoViewsetPermissions action permission for %s' % action)

    def get_list_actions(self, viewset):
        """
        Get the list actions; these will not have get_object() invoked when checking permissions
        """
        viewset_class = viewset.__class__

        # Is this really ok to be caching on this another object?
        if not hasattr(viewset_class, '_saved_permission_list_actions'):
            viewset_class._saved_permission_list_actions = set(self.default_list_routes)

            # Determine any `@list_route` decorated methods on the viewset
            for methodname in dir(viewset_class):
                method = getattr(viewset_class, methodname)

                # pre-3.9 DRF
                http_methods = getattr(method, 'bind_to_methods', None)
                # Only certain methods do not require an object
                if http_methods and all(m.lower() in ('header', 'get', 'post',) for m in http_methods):
                    if getattr(method, 'detail', None) is False:
                        viewset_class._saved_permission_list_actions.add(methodname)

                # post-3.9 DRF
                if not http_methods and hasattr(method, 'mapping'):
                    if all(m.lower() in ('header', 'get', 'post',) for m in getattr(method, 'mapping').keys()):
                        if getattr(method, 'detail', None) is False: # the detail remains accessible - just bind_to_methods' gone.
                            viewset_class._saved_permission_list_actions.add(methodname)

        return viewset_class._saved_permission_list_actions

    def has_permission(self, request, viewset):

        action = getattr(viewset, 'action', None)

        # Handles OPTIONS requests
        # Doing an OPTIONS call directly will result in an action of 'metadata'
        # See http://www.django-rest-framework.org/api-guide/metadata/
        # The BrowsableAPIRenderer will also check permissions to decide whether
        # to show the 'OPTIONS' button - in this case the action is None. It
        # appears that the default behaviour for OPTIONS should be no authentication
        # in the context of CORS.
        # See https://github.com/encode/django-rest-framework/issues/5616
        # Browseable APIs are not supposed to be enabled on production (see ROOT one),
        # thus we only care when DEBUG's set, and this will not have side effects
        # if a dev choose to use OPTIONS for some specific purpose.
        if request.method == 'OPTIONS' and settings.DEBUG:
            return True

        user = request.user
        perms = self.get_permissions_for_action(action, viewset)

        # Check permissions for action available irrespective of object
        if user.has_perms(perms):
            return True

        # Action relates to object, check object level permission
        if action not in self.get_list_actions(viewset):
            # This should invoke self.check_object_permissions() which
            # will then invoke has_object_permission()
            viewset.get_object()   # will raise an exception if permission denied
            return True

        return False

    def has_object_permission(self, request, viewset, obj):
        action = viewset.action
        # Handles OPTIONS requests
        if request.method == 'OPTIONS' and settings.DEBUG:
            return True
        perms = self.get_permissions_for_action(action, viewset)
        user = request.user
        return user.has_perms(perms, obj)
