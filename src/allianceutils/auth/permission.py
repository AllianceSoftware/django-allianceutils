from collections.abc import Iterable
import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
import warnings

from django.contrib.auth import get_backends
from django.db.models import Model
from django.http import Http404
from django.http import HttpRequest
from django.urls import resolve
from django.urls import reverse
import rules.permissions # type: ignore[import-not-found]

logger = logging.getLogger("allianceutils")


class NoDefaultPermissionsMeta:
    """
    Set empty default permissions so django does not create any. They will be generated dynamically from a CSV.

    See :any:`django.db.models.Options.default_permissions` for more information
    """

    default_permissions = ()


class PermissionNotImplementedError(NotImplementedError):
    pass


class AmbiguousGlobalPermissionWarning(Warning):
    """Cannot determine whether a permission is global or per-object"""

    pass


def identify_global_perms(perms: Union[str, Iterable[str]]) -> Tuple[List[str], List[str]]:
    """Given a permission or a list of permissions identifies which are global and which are object permissions

    returns (global permission list, object permission list)
    """
    backends = get_backends()

    if isinstance(perms, str):
        perms = [perms]

    global_perms = []
    object_perms = []

    for perm in perms:
        # We use 2 vars to keep track because something could be both a global & an object-level permission
        # in different backends
        is_global = None
        is_object = None
        for backend in backends:
            if hasattr(backend, "is_global_perm"):
                try:
                    if backend.is_global_perm(perm):
                        is_global = True
                        global_perms.append(perm)
                    else:
                        is_object = True
                        object_perms.append(perm)
                    break
                # Permission doesn't exist in the backend
                except ValueError:
                    pass
            elif isinstance(backend, rules.permissions.ObjectPermissionBackend):
                rule = rules.permissions.permissions.get(perm)
                if rule:
                    if rule.num_args == 1:
                        is_global = True
                        global_perms.append(perm)
                    elif rule.num_args == 2:
                        is_object = True
                        object_perms.append(perm)
                    else:
                        raise ValueError(f"Cannot understand arguments for django-rules {perm}")

        if not is_global and not is_object:
            global_perms.append(perm)
            # TODO: should we make this configurable?
            # if you have a permission defined outside of csvpermissions (eg in django-rules)
            # then there's no way to know whether it's global or per-object
            #
            # we could also introspect django-rules if that's the other place a permission might be defined
            warnings.warn(
                f"Permission {perm} not found in backend that supports is_global_perm",
                AmbiguousGlobalPermissionWarning,
            )

    return global_perms, object_perms


def reverse_if_probably_allowed(
    request: HttpRequest,
    viewname: str,
    object: Optional[Model] = None,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]]= None,
) -> Optional[str]:
    """
    Call reverse() on a view. Try to guess whether the current user has permission to access that view
    If they do then return the URL otherwise return None

    THIS IS NOT 100% RELIABLE and should only be used for selectively displaying links where the
    worst that may happen is the user clicks on a link and gets a 403 response

    If unsure, this function will return the URL
    """

    if kwargs is None:
        kwargs = dict()

    if args is None:
        args = []

    target_href = reverse(viewname, args=args, kwargs=kwargs)
    target_match = resolve(target_href)

    # ------------------------------------------
    # fully instantiating and running a view might be costly (and have side effects)
    # so we just do a permission check ourselves. This is not 100% accurate (it knows nothing
    # about has_perm customisations for example) but in the worst case the user will simply
    # see a link that gives them a 403 when they try to click on it
    target_class = getattr(target_match.func, "view_class", None)

    if not target_class:
        # we only handle classes, not view functions
        warnings.warn(f"Not sure how to check permission on view func {target_match.func}")
        # TODO: reinstate this check in KF292
        # if settings.DEBUG:
        #     raise NotImplementedError("guess_view_permission() doesn't work with " + str(target_match.func))

    perm: Optional[Union[str, List[str]]] = None
    perm_object = None
    if target_perm := getattr(target_class, "permission_required", None):
        # optimisation: if it looks like this has only static global permission(s) then
        # we can statically check the permissions without creating a fake request
        global_perms, object_perms = identify_global_perms(target_perm)

        if global_perms and not object_perms:
            perm = global_perms
        elif object_perms and object is not None:
            perm = object_perms
            perm_object = object

    if not perm:
        if target_class is not None and getattr(target_class, "has_permission", None):
            # Create a synthetic request
            # - we don't want to simulate a full request cycle because that will be quite slow
            # - this minimal request setup is what django.test.client.Client does for login/logout
            # - if there is any middleware that modifies the request then you'll have to simulate that here
            # - we don't want to use the real request because we don't want to minimise the chance of side effects leaking out
            # - some links (eg logout) will have side effects.

            synthetic_request = HttpRequest()
            synthetic_request.user = request.user
            synthetic_request.session = request.session

            view = target_class()
            view.setup(synthetic_request, *args, **kwargs)
            # has_permission
            try:
                return target_href if view.has_permission() else None
            except Http404:
                # if the route didn't exist at all then the earlier reverse() would have failed
                # so a 404 here usually means the route exists but the parameters were wrong and get_object() failed
                return None
            except Exception as e:
                logger.warning(f"Got exception looking at view {viewname} ({e})")
                return None

        else:
            # Possible things to check:
            # - get_permission_required
            if getattr(target_class, "permission_required", None) is None:
                # Assume view was public: it has a permission_required but it's None
                # (is this the best way of doing this? there's no django convention to explicitly mark
                # something as public)
                return target_href
            else:
                warnings.warn(f"Not sure how to check permission on view class {target_class}")
                return target_href

            # TODO: reinstate this check in KF292
            # if settings.DEBUG:
            #     raise NotImplementedError("guess_view_permission() doesn't work with " + str(target_class))

    if not perm:
        raise NotImplementedError(f"Can't find a permission to check for view class {target_class}")

    if isinstance(perm, str):
        perm = [perm]

    return target_href if request.user.has_perms(perm, perm_object) else None
