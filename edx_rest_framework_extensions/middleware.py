"""
Middleware to ensure best practices of DRF endpoints.
"""
import logging

from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication

from .permissions import JwtHasScope

log = logging.getLogger(__name__)


class EnsureJWTAuthSettingsMiddleware(object):
    """
    Django middleware object that ensures the proper Permission classes
    are set on all endpoints that use JWTAuthentication.
    """
    _required_permission_classes = (JwtHasScope,)
    _view_does_not_support_scopes = 'VIEW_DOES_NOT_SUPPORT_SCOPES'

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
        view_permission_classes = getattr(view_class, 'permission_classes', tuple())

        for perm_class in self._required_permission_classes:

            if not self._includes_base_class(view_permission_classes, perm_class):
                log.warning(
                    u"The view %s allows Jwt Authentication but needs to include the %s permission class.",
                    view_class.__name__,
                    perm_class.__name__,
                )

        view_class.permission_classes = view_permission_classes
        view_class.permission_classes += self._required_permission_classes

    def _add_missing_jwt_scopes(self, view_class):
        """
        Adds restricting scopes if none already exist for Jwt based authentication.
        """
        view_required_scopes = getattr(view_class, 'required_scopes', [])
        if not view_required_scopes:
            view_class.required_scopes = [self._view_does_not_support_scopes]

    def process_view(self, request, view_func, view_args, view_kwargs):  # pylint: disable=unused-argument
        view_class = getattr(view_func, 'view_class', view_func)

        view_authentication_classes = getattr(view_class, 'authentication_classes', tuple())
        if self._includes_base_class(view_authentication_classes, BaseJSONWebTokenAuthentication):
            self._add_missing_jwt_permission_classes(view_class)
            self._add_missing_jwt_scopes(view_class)
