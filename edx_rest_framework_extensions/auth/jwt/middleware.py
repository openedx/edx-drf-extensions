"""
Middleware supporting JWT Authentication.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.utils.deprecation import MiddlewareMixin
from edx_django_utils import monitoring
from edx_django_utils.cache import RequestCache
from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication

from edx_rest_framework_extensions.auth.jwt.cookies import (
    jwt_cookie_name,
    jwt_cookie_header_payload_name,
    jwt_cookie_signature_name,
)
from edx_rest_framework_extensions.auth.jwt.constants import JWT_DELIMITER
from edx_rest_framework_extensions.permissions import LoginRedirectIfUnauthenticated, NotJwtRestrictedApplication

log = logging.getLogger(__name__)
USE_JWT_COOKIE_HEADER = 'HTTP_USE_JWT_COOKIE'


class EnsureJWTAuthSettingsMiddleware(MiddlewareMixin):
    """
    Django middleware object that ensures the proper Permission classes
    are set on all endpoints that use JWTAuthentication.
    """
    _required_permission_classes = (NotJwtRestrictedApplication,)

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
            if not _includes_base_class(permission_classes, perm_class):
                message = (
                    u"The view %s allows Jwt Authentication. The required permission class, %s,",
                    u" was automatically added."
                )
                log.info(
                    message,
                    view_class.__name__,
                    perm_class.__name__,
                )
                classes_to_add.append(perm_class)

        if classes_to_add:
            view_class.permission_classes += tuple(classes_to_add)

    def process_view(self, request, view_func, view_args, view_kwargs):  # pylint: disable=unused-argument
        view_class = _get_view_class(view_func)

        view_authentication_classes = getattr(view_class, 'authentication_classes', tuple())
        if _includes_base_class(view_authentication_classes, BaseJSONWebTokenAuthentication):
            self._add_missing_jwt_permission_classes(view_class)


class JwtRedirectToLoginIfUnauthenticatedMiddleware(MiddlewareMixin):
    """
    Middleware enables the DRF JwtAuthentication authentication class for endpoints
    using the LoginRedirectIfUnauthenticated permission class.

    Enables a DRF view to redirect the user to login when they are unauthenticated.
    It automatically enables JWT-cookie-based authentication by setting the
    `USE_JWT_COOKIE_HEADER` for endpoints using the LoginRedirectIfUnauthenticated
    permission.

    This can be used to convert a plain Django view using @login_required into a
    DRF APIView, which is useful to enable our DRF JwtAuthentication class.

    Usage Notes:
    - This middleware must be added before JwtAuthCookieMiddleware.
    - Only affects endpoints using the LoginRedirectIfUnauthenticated permission class.

    See https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/oauth_dispatch/docs/decisions/0009-jwt-in-session-cookie.rst  # noqa E501 line too long
    """
    def get_login_url(self, request):  # pylint: disable=unused-argument
        """
        Return None for default login url.

        Can be overridden for slow-rollout or A/B testing of transition to other login mechanisms.
        """
        return None

    def is_jwt_auth_enabled_with_login_required(self, request, view_func):  # pylint: disable=unused-argument
        """
        Returns True if JwtAuthentication is enabled with the LoginRedirectIfUnauthenticated permission class.

        Can be overridden for slow roll-out or A/B testing.
        """
        return self._is_login_required_found()

    def process_view(self, request, view_func, view_args, view_kwargs):  # pylint: disable=unused-argument
        """
        Enables Jwt Authentication for endpoints using the LoginRedirectIfUnauthenticated permission class.
        """
        self._check_and_cache_login_required_found(view_func)
        if self.is_jwt_auth_enabled_with_login_required(request, view_func):
            request.META[USE_JWT_COOKIE_HEADER] = 'true'

    def process_response(self, request, response):
        """
        Redirects unauthenticated users to login when LoginRedirectIfUnauthenticated permission class was used.
        """
        if self._is_login_required_found() and not request.user.is_authenticated:
            login_url = self.get_login_url(request)
            return login_required(function=lambda request: None, login_url=login_url)(request)

        return response

    _REQUEST_CACHE_NAMESPACE = 'JwtRedirectToLoginIfUnauthenticatedMiddleware'
    _LOGIN_REQUIRED_FOUND_CACHE_KEY = 'login_required_found'

    def _get_request_cache(self):
        return RequestCache(self._REQUEST_CACHE_NAMESPACE).data

    def _is_login_required_found(self):
        """
        Returns True if LoginRedirectIfUnauthenticated permission was found, and False otherwise.
        """
        return self._get_request_cache().get(self._LOGIN_REQUIRED_FOUND_CACHE_KEY, False)

    def _check_and_cache_login_required_found(self, view_func):
        """
        Checks for LoginRedirectIfUnauthenticated permission and caches the result.
        """
        view_class = _get_view_class(view_func)
        view_permission_classes = getattr(view_class, 'permission_classes', tuple())
        is_login_required_found = _includes_base_class(view_permission_classes, LoginRedirectIfUnauthenticated)
        self._get_request_cache()[self._LOGIN_REQUIRED_FOUND_CACHE_KEY] = is_login_required_found


class JwtAuthCookieMiddleware(MiddlewareMixin):
    """
    Reconstitutes JWT auth cookies for use by API views which use the JwtAuthentication
    authentication class.

    We split the JWT across two separate cookies in the browser for security reasons. This
    middleware reconstitutes the full JWT into a new cookie on the request object for use
    by the JwtAuthentication class.

    See the full decision here:
        https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/oauth_dispatch/docs/decisions/0009-jwt-in-session-cookie.rst

    Also, sets the metric 'request_jwt_cookie' with one of the following values:
        'success': Value when reconstitution is successful.
        'not-requested': Value when jwt cookie authentication was not requested by the client.
        'missing-both': Value when both cookies are missing and reconstitution is not possible.
        'missing-XXX': Value when one of the 2 required cookies is missing.  XXX will be
            replaced by the cookie name, which may be set as a setting.  Defaults would
            be 'missing-edx-jwt-cookie-header-payload' or 'missing-edx-jwt-cookie-signature'.

    This middleware must appear before any AuthenticationMiddleware.  For example::

        MIDDLEWARE_CLASSES = (
            'edx_rest_framework_extensions.auth.jwt.middleware.JwtAuthCookieMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        )

    """

    def _get_missing_cookie_message_and_metric(self, cookie_name):
        """ Returns tuple with missing cookie (log_message, metric_value) """
        cookie_missing_message = '{} cookie is missing. JWT auth cookies will not be reconstituted.'.format(
                cookie_name
        )
        request_jwt_cookie = 'missing-{}'.format(cookie_name)
        return cookie_missing_message, request_jwt_cookie

    # Note: Using `process_view` over `process_request` so JwtRedirectToLoginIfUnauthenticatedMiddleware which
    # uses `process_view` can update the request before this middleware. Method `process_request` happened too early.
    def process_view(self, request, view_func, view_args, view_kwargs):  # pylint: disable=unused-argument
        """
        Reconstitute the full JWT and add a new cookie on the request object.
        """
        use_jwt_cookie_requested = request.META.get(USE_JWT_COOKIE_HEADER)
        header_payload_cookie = request.COOKIES.get(jwt_cookie_header_payload_name())
        signature_cookie = request.COOKIES.get(jwt_cookie_signature_name())

        if not use_jwt_cookie_requested:
            metric_value = 'not-requested'
        elif header_payload_cookie and signature_cookie:
            # Reconstitute JWT auth cookie if split cookies are available and jwt cookie
            # authentication was requested by the client.
            request.COOKIES[jwt_cookie_name()] = '{}{}{}'.format(
                header_payload_cookie,
                JWT_DELIMITER,
                signature_cookie,
            )
            metric_value = 'success'
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
            metric_value = 'missing-both'

        monitoring.set_custom_metric('request_jwt_cookie', metric_value)


def _includes_base_class(iter_classes, base_class):
    """
    Returns whether any class in iter_class is a subclass of the given base_class.
    """
    return any(
        issubclass(current_class, base_class) for current_class in iter_classes,
    )


def _get_view_class(view_func):
    # Views as functions store the view's class in the 'view_class' attribute.
    # Viewsets store the view's class in the 'cls' attribute.
    view_class = getattr(
        view_func,
        'view_class',
        getattr(view_func, 'cls', view_func),
    )
    return view_class
