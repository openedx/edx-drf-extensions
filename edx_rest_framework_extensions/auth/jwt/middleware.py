"""
Middleware supporting JWT Authentication.
"""
import logging

from edx_django_utils import monitoring
from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication

from edx_rest_framework_extensions.auth.jwt.cookies import (
    jwt_cookie_name,
    jwt_cookie_header_payload_name,
    jwt_cookie_signature_name,
)
from edx_rest_framework_extensions.auth.jwt.constants import JWT_DELIMITER
from edx_rest_framework_extensions.permissions import NotJwtRestrictedApplication

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
        # Views as functions store the view's class in the 'view_class' attribute.
        # Viewsets store the view's class in the 'cls' attribute.
        view_class = getattr(
            view_func,
            'view_class',
            getattr(view_func, 'cls', view_func),
        )

        view_authentication_classes = getattr(view_class, 'authentication_classes', tuple())
        if self._includes_base_class(view_authentication_classes, BaseJSONWebTokenAuthentication):
            self._add_missing_jwt_permission_classes(view_class)


class JwtAuthCookieMiddleware(object):
    """
    Reconstitutes JWT auth cookies for use by API views which use the JwtAuthentication
    authentication class.

    We split the JWT across two separate cookies in the browser for security reasons. This
    middleware reconstitutes the full JWT into a new cookie on the request object for use
    by the JwtAuthentication class.

    See the full decision here:
        https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/oauth_dispatch/docs/decisions/0009-jwt-in-session-cookie.rst

    Also, sets the metric 'request_jwt_cookie' with one of the following values:
        'yes': Value when reconstitution is successful.
        'no': Value when both cookies are missing and reconstitution is not possible.
        'missing-XXX': Value when one of the 2 required cookies is missing.  XXX will be
            replaced by the cookie name, which may be set as a setting.  Defaults would
            be 'missing-edx-jwt-cookie-header-payload' or 'missing-edx-jwt-cookie-signature'.

    """

    def _get_missing_cookie_message_and_metric(self, cookie_name):
        """ Returns tuple with missing cookie (log_message, metric_value) """
        cookie_missing_message = '{} cookie is missing. JWT auth cookies will not be reconstituted.'.format(
                cookie_name
        )
        request_jwt_cookie = 'missing-{}'.format(cookie_name)
        return cookie_missing_message, request_jwt_cookie

    def process_request(self, request):
        """
        Reconstitute the full JWT and add a new cookie on the request object.
        """
        header_payload_cookie = request.COOKIES.get(jwt_cookie_header_payload_name())
        signature_cookie = request.COOKIES.get(jwt_cookie_signature_name())

        # Reconstitute JWT auth cookie if split cookies are available.
        if header_payload_cookie and signature_cookie:
            request.COOKIES[jwt_cookie_name()] = '{}{}{}'.format(
                header_payload_cookie,
                JWT_DELIMITER,
                signature_cookie,
            )
            metric_value = 'yes'
        elif header_payload_cookie or signature_cookie:
            # Log unexpected case of only finding one cookie.
            if not header_payload_cookie:
                log_message, metric_value = self._get_missing_cookie_message_and_metric(
                    jwt_cookie_header_payload_name()
                )
            if not signature_cookie:
                log_message, metric_value = self._get_missing_cookie_message_and_metric(
                    jwt_cookie_signature_name()
                )
            log.warning(log_message)
        else:
            metric_value = 'no'

        monitoring.set_custom_metric('request_jwt_cookie', metric_value)
