"""
Middleware supporting JWT Authentication.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.middleware import get_user
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject
from edx_django_utils.cache import RequestCache
from edx_django_utils.monitoring import set_custom_attribute
from rest_framework.permissions import OperandHolder, SingleOperandHolder
from rest_framework.request import Request
from rest_framework.settings import api_settings
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from edx_rest_framework_extensions.auth.jwt.authentication import (
    set_flag_is_request_user_set_for_jwt_auth,
)
from edx_rest_framework_extensions.auth.jwt.constants import JWT_DELIMITER
from edx_rest_framework_extensions.auth.jwt.cookies import (
    jwt_cookie_header_payload_name,
    jwt_cookie_name,
    jwt_cookie_signature_name,
)
from edx_rest_framework_extensions.config import ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE
from edx_rest_framework_extensions.permissions import (
    LoginRedirectIfUnauthenticated,
    NotJwtRestrictedApplication,
)
from edx_rest_framework_extensions.settings import get_setting


log = logging.getLogger(__name__)


class EnsureJWTAuthSettingsMiddleware(MiddlewareMixin):
    """
    Django middleware object that ensures the proper Permission classes
    are set on all endpoints that use JWTAuthentication.
    """
    _required_permission_classes = (NotJwtRestrictedApplication,)

    def _iter_included_base_classes(self, view_permissions):
        """
        Yield all the permissions that are encapsulated in provided view_permissions, directly or as
        a part of DRF's composed permissions.
        """
        # Not all permissions are classes, some will be OperandHolder
        # objects from DRF. So we have to crawl all those and expand them to see
        # if our target classes are inside the conditionals somewhere.
        for permission in view_permissions:
            # Composition using DRF native support in 3.9+:
            # IsStaff | IsSuperuser -> [IsStaff, IsSuperuser]
            # IsOwner | IsStaff | IsSuperuser -> [IsOwner | IsStaff, IsSuperuser]
            if isinstance(permission, OperandHolder):
                decomposed_permissions = [permission.op1_class, permission.op2_class]
                yield from self._iter_included_base_classes(decomposed_permissions)
            elif isinstance(permission, SingleOperandHolder):
                yield permission.op1_class
            else:
                yield permission

    def _add_missing_jwt_permission_classes(self, view_class):
        """
        Adds permissions classes that should exist for Jwt based authentication,
        if needed.
        """
        classes_to_add = []
        view_permissions = list(getattr(view_class, 'permission_classes', []))

        for perm_class in self._required_permission_classes:
            if not _includes_base_class(self._iter_included_base_classes(view_permissions), perm_class):
                message = (
                    "The view %s allows Jwt Authentication. The required permission class, %s,",
                    " was automatically added."
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
        if _includes_base_class(view_authentication_classes, JSONWebTokenAuthentication):
            self._add_missing_jwt_permission_classes(view_class)


class JwtRedirectToLoginIfUnauthenticatedMiddleware(MiddlewareMixin):
    """
    Middleware enables the DRF JwtAuthentication authentication class for endpoints
    using the LoginRedirectIfUnauthenticated permission class.

    Enables a DRF view to redirect the user to login when they are unauthenticated.

    This can be used to convert a plain Django view using @login_required into a
    DRF APIView, which is useful to enable our DRF JwtAuthentication class.

    Usage Notes:
    - This middleware must be added before JwtAuthCookieMiddleware.
    - Only affects endpoints using the LoginRedirectIfUnauthenticated permission class.

    See https://github.com/openedx/edx-platform/blob/master/openedx/core/djangoapps/oauth_dispatch/docs/decisions/0009-jwt-in-session-cookie.rst  # noqa E501 line too long
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
        # Note: Rather than caching here, this could be called directly in process_response based on the request,
        # which would require using reverse to determine the view.
        self._check_and_cache_login_required_found(view_func)

    def process_response(self, request, response):
        """
        Redirects unauthenticated users to login when LoginRedirectIfUnauthenticated permission class was used.
        """
        if self._is_login_required_found() and not request.user.is_authenticated:
            login_url = self.get_login_url(request)  # pylint: disable=assignment-from-none
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

    Has side effect of setting request.user to be available for Jwt Authentication
    to Middleware using process_view, but not process_request.

    We split the JWT across two separate cookies in the browser for security reasons. This
    middleware reconstitutes the full JWT into a new cookie on the request object for use
    by the JwtAuthentication class.

    See the full decision here:
        https://github.com/openedx/edx-platform/blob/master/openedx/core/djangoapps/oauth_dispatch/docs/decisions/0009-jwt-in-session-cookie.rst

    Also, sets the custom attribute 'request_jwt_cookie' with one of the following values:
        'success': Value when reconstitution is successful.
        'not-requested': Value when jwt cookie authentication was not requested by the client.
        'missing-both': Value when both cookies are missing and reconstitution is not possible.
        'missing-XXX': Value when one of the 2 required cookies is missing.  XXX will be
            replaced by the cookie name, which may be set as a setting.  Defaults would
            be 'missing-edx-jwt-cookie-header-payload' or 'missing-edx-jwt-cookie-signature'.

    This middleware must appear before any AuthenticationMiddleware.  For example::

        MIDDLEWARE = (
            'edx_rest_framework_extensions.auth.jwt.middleware.JwtAuthCookieMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        )

    """
    def _get_missing_cookie_message(self, cookie_name):
        """ Returns missing cookie log_message """
        return '{} cookie is missing. JWT auth cookies will not be reconstituted.'.format(
                cookie_name
        )

    # Note: Using `process_view` over `process_request` so JwtRedirectToLoginIfUnauthenticatedMiddleware which
    # uses `process_view` can update the request before this middleware. Method `process_request` happened too early.
    def process_view(self, request, view_func, view_args, view_kwargs):  # pylint: disable=unused-argument
        """
        Reconstitute the full JWT and add a new cookie on the request object.

        Additionally, may add the user to the request to make it available in process_view. (See below.)
        """
        assert hasattr(request, 'session'), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE setting to insert 'django.contrib.sessions.middleware.SessionMiddleware'."  # noqa E501 line too long

        header_payload_cookie = request.COOKIES.get(jwt_cookie_header_payload_name())
        signature_cookie = request.COOKIES.get(jwt_cookie_signature_name())

        if header_payload_cookie and signature_cookie:
            # Reconstitute JWT auth cookie if split cookies are available.
            request.COOKIES[jwt_cookie_name()] = '{}{}{}'.format(
                header_payload_cookie,
                JWT_DELIMITER,
                signature_cookie,
            )
        elif header_payload_cookie or signature_cookie:
            # Log unexpected case of only finding one cookie.
            if not header_payload_cookie:
                log_message = self._get_missing_cookie_message(jwt_cookie_header_payload_name())
            if not signature_cookie:
                log_message = self._get_missing_cookie_message(jwt_cookie_signature_name())
            log.warning(log_message)

        has_reconstituted_jwt_cookie = jwt_cookie_name() in request.COOKIES
        # .. custom_attribute_name: has_jwt_cookie
        # .. custom_attribute_description: Enables us to see requests which have the full reconstituted
        #      JWT cookie. If this attribute is missing, it is assumed to be False.
        set_custom_attribute('has_jwt_cookie', has_reconstituted_jwt_cookie)

        # DRF authentication does not set the request.user early enough for it to be used in process_request/
        # process_view of middleware. This code enables JWT cookie authentication to set the request.user for
        # middleware, before it will presumably happen again during DRF authentication.
        # For more info on DRF and the request.user, see
        # https://github.com/jpadilla/django-rest-framework-jwt/issues/45#issuecomment-74996698
        #
        # If the user has already been authenticated, we already have a user and intentionally avoid resetting it. As of
        # Oct 2023, this would likely be due to session authentication in middleware. It is thus important for
        # JwtAuthentication to verify that the session user and JWT user match. It is possible that this would be better
        # handled through a more traditional AuthenticationMiddleware that handles both JWT cookies and sessions in
        # the future.
        if has_reconstituted_jwt_cookie and get_setting(ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE):
            # Since this call to the user is not made lazily, and has the potential to cause issues, we
            # ensure it is only used in the case of ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE.
            if not get_user(request).is_authenticated:
                # Similar to django/contrib/auth/middleware.py AuthenticationMiddleware.
                set_flag_is_request_user_set_for_jwt_auth()
                request.user = SimpleLazyObject(lambda: _get_cached_user_from_jwt(request, view_func))


def _get_module_request_cache():
    return RequestCache(__name__).data


def _get_cached_user_from_jwt(request, view_func):
    """
    Returns cached user from JWT authentication.

    Performs JWT authentication if not already cached.
    """
    # Similar to django/contrib/auth/middleware.py get_user.
    _JWT_USER_CACHE_KEY = '_cached_jwt_user'
    if _get_module_request_cache().get(_JWT_USER_CACHE_KEY, None) is None:
        cached_jwt_user = _get_user_from_jwt(request, view_func)
        _get_module_request_cache()[_JWT_USER_CACHE_KEY] = cached_jwt_user
    return _get_module_request_cache()[_JWT_USER_CACHE_KEY]


def _get_user_from_jwt(request, view_func):
    """
    Performs JWT Authentication and returns the user, or AnonymousUser if the user is
    not authenticated.

    Uses the JWT authentication class associated the view. If not found, processing is skipped.
    """
    # .. custom_attribute_name: set_user_from_jwt_status
    # .. custom_attribute_description: Provides the status of setting the user from the JWT, using one of the
    #      following values: success, auth-failed, jwt-auth-class-not-found, and unknown-exception.
    try:
        jwt_authentication_class = _get_jwt_authentication_class(view_func)
        if jwt_authentication_class:
            user_jwt = jwt_authentication_class().authenticate(Request(
                request,
                parsers=api_settings.DEFAULT_PARSER_CLASSES
            ))
            if user_jwt is not None:
                set_custom_attribute('set_user_from_jwt_status', 'success')
                return user_jwt[0]
            else:
                set_custom_attribute('set_user_from_jwt_status', 'auth-failed')
                log.debug('Jwt Authentication failed and request.user could not be set.')
        else:
            set_custom_attribute('set_user_from_jwt_status', 'jwt-auth-class-not-found')
            log.debug(
                'Jwt Authentication expected, but view %s is not using a JwtAuthentication class.', view_func
            )
    except Exception:  # pylint: disable=broad-except
        set_custom_attribute('set_user_from_jwt_status', 'unknown-exception')
        log.exception('Unknown Jwt Authentication error attempting to retrieve the user.')  # pragma: no cover

    return AnonymousUser()


def _get_jwt_authentication_class(view_func):
    """
    Returns the first DRF Authentication class that is a subclass of JSONWebTokenAuthentication
    """
    view_class = _get_view_class(view_func)
    view_authentication_classes = getattr(view_class, 'authentication_classes', tuple())
    if _includes_base_class(view_authentication_classes, JSONWebTokenAuthentication):
        return next(
            current_class for current_class in view_authentication_classes
            if issubclass(current_class, JSONWebTokenAuthentication)
        )
    return None


def _includes_base_class(iter_classes, base_class):
    """
    Returns whether any class in iter_class is a subclass of the given base_class.
    """
    return any(
        issubclass(current_class, base_class) for current_class in iter_classes
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
