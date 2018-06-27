"""
Middleware to ensure best practices of DRF endpoints.
"""
import logging

from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication

from .permissions import NotJwtRestrictedApplication

log = logging.getLogger(__name__)


class EnsureJWTAuthSettingsMiddleware(object):
    """
    Django middleware object that ensures the proper Permission classes
    are set on all endpoints that use JWTAuthentication.
    """
    _required_permission_classes = (NotJwtRestrictedApplication,)

    def _includes_base_class(self, iter_classes, base_class):
        """
        Returns whether any class in iter_class is a subclass of the given base_class.
        """
        return any(
            issubclass(auth_class, base_class) for auth_class in iter_classes,
        )

    def _add_missing_jwt_permission_classes(self, view_class):
        """
        Adds permissions classes that should exist for Jwt based authentication,
        if needed.
        """
        view_permissions = list(getattr(view_class, 'permission_classes', []))

        # Not all permissions are classes, some will be ConditionalPermission
        # objects from the rest_condition library. So we have to crawl all those
        # and expand them to see if our target classes are inside the
        # conditionals somewhere.
        permission_classes = []
        classes_to_add = []
        while view_permissions:
            permission = view_permissions.pop()
            if not hasattr(permission, 'perms_or_conds'):
                permission_classes.append(permission)
            else:
                for child in getattr(permission, 'perms_or_conds', []):
                    view_permissions.append(child)

        for perm_class in self._required_permission_classes:
            if not self._includes_base_class(permission_classes, perm_class):
                log.warning(
                    u"The view %s allows Jwt Authentication but needs to include the %s permission class (adding it for you)",
                    view_class.__name__,
                    perm_class.__name__,
                )
                classes_to_add.append(perm_class)

        if classes_to_add:
            view_class.permission_classes += tuple(classes_to_add)

    def process_view(self, request, view_func, view_args, view_kwargs):  # pylint: disable=unused-argument
        view_class = getattr(view_func, 'view_class', view_func)

        view_authentication_classes = getattr(view_class, 'authentication_classes', tuple())
        if self._includes_base_class(view_authentication_classes, BaseJSONWebTokenAuthentication):
            self._add_missing_jwt_permission_classes(view_class)
