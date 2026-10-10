""" JWT Authentication class. """

import logging

from django.contrib.auth import get_user_model
from django.middleware.csrf import CsrfViewMiddleware
from edx_django_utils.cache import RequestCache
from edx_django_utils.monitoring import set_custom_attribute
from jwt import exceptions as jwt_exceptions
from rest_framework import exceptions
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from edx_rest_framework_extensions.auth.jwt.decoder import (
    configured_jwt_decode_handler,
    unsafe_jwt_decode_handler,
)
from edx_rest_framework_extensions.config import (
    ENABLE_JWT_AND_LMS_USER_EMAIL_MATCH,
    ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE,
)
from edx_rest_framework_extensions.settings import get_setting


logger = logging.getLogger(__name__)


class JwtAuthenticationError(exceptions.AuthenticationFailed):
    """
    Custom base class for all exceptions
    """


class JwtSessionUserMismatchError(JwtAuthenticationError):
    pass


class JwtUserEmailMismatchError(JwtAuthenticationError):
    pass


class CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        # Return the failure reason instead of an HttpResponse
        return reason


class JwtAuthentication(JSONWebTokenAuthentication):
    """
    JSON Web Token based authentication.

    This authentication class is useful for authenticating a JWT using a secret key. Clients should authenticate by
    passing the token key in the "Authorization" HTTP header, prepended with the string `"JWT "`.

    This class relies on the JWT_AUTH being configured for the application as well as JWT_PAYLOAD_USER_ATTRIBUTES
    being configured in the EDX_DRF_EXTENSIONS config.

    At a minimum, the JWT payload must contain a username. If an email address
    is provided in the payload, it will be used to update the retrieved user's
    email address associated with that username.

    Example Header:
        Authorization: JWT eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYzJiNzIwMTE0YmIwN2I0NjVlODQzYTc0ZWM2ODNlNiIs
        ImFkbWluaXN0cmF0b3IiOmZhbHNlLCJuYW1lIjoiaG9ub3IiLCJleHA.QHDXdo8gDJ5p9uOErTLZtl2HK_61kgLs71VHp6sLx8rIqj2tt9yCfc_0
        JUZpIYMkEd38uf1vj-4HZkzeNBnZZZ3Kdvq7F8ZioREPKNyEVSm2mnzl1v49EthehN9kwfUgFgPXfUh-pCvLDqwCCTdAXMcTJ8qufzEPTYYY54lY
    """

    def get_jwt_claim_attribute_map(self):
        """ Returns a mapping of JWT claims to user model attributes.

        Returns
            dict
        """
        return get_setting('JWT_PAYLOAD_USER_ATTRIBUTE_MAPPING')

    def get_jwt_claim_mergeable_attributes(self):
        """ Returns a list of user model attributes that should be merged into from the JWT.

        Returns
            list
        """
        return get_setting('JWT_PAYLOAD_MERGEABLE_USER_ATTRIBUTES')

    def authenticate(self, request):
        # .. custom_attribute_name: jwt_auth_result
        # .. custom_attribute_description: The result of the JWT authenticate process,
        #      which can having the following values:
        #        'n/a': When JWT Authentication doesn't apply.
        #        'success-auth-header': Successfully authenticated using the Authorization header.
        #        'success-cookie': Successfully authenticated using a JWT cookie.
        #        'forgiven-failure': Returns None instead of failing for JWT cookies. This handles
        #          the case where expired cookies won't prevent another authentication class, like
        #          SessionAuthentication, from having a chance to succeed.
        #          See docs/decisions/0002-remove-use-jwt-cookie-header.rst for details.
        #        'failed-auth-header': JWT Authorization header authentication failed. This prevents
        #          other authentication classes from attempting authentication.
        #        'failed-cookie': JWT cookie authentication failed. This prevents other
        #          authentication classes from attempting authentication.
        #        'user-mismatch-failure': JWT vs session user mismatch found for what would have been
        #          a forgiven-failure, but instead, the JWT failure will be final.
        #        'user-mismatch-enforced-failure': JWT vs session user mismatch found for what would
        #          have been a successful JWT authentication, but we are enforcing a match, and thus
        #          we fail authentication.

        is_authenticating_with_jwt_cookie = self.is_authenticating_with_jwt_cookie(request)
        try:
            user_and_auth = super().authenticate(request)

            # Unauthenticated, CSRF validation not required
            if not user_and_auth:
                set_custom_attribute('jwt_auth_result', 'n/a')
                return user_and_auth

            if get_setting(ENABLE_JWT_AND_LMS_USER_EMAIL_MATCH):
                is_email_mismatch = self._is_jwt_and_lms_user_email_mismatch(request, user_and_auth[0])
                if is_email_mismatch:
                    raise JwtUserEmailMismatchError(
                        'Failing JWT authentication due to jwt user email mismatch '
                        'with lms user email.'
                    )

            # Not using JWT cookie, CSRF validation not required
            if not is_authenticating_with_jwt_cookie:
                set_custom_attribute('jwt_auth_result', 'success-auth-header')
                return user_and_auth

            self.enforce_csrf(request)

            # CSRF passed validation with authenticated user

            # adds additional monitoring for mismatches; and raises errors in certain cases
            is_mismatch = self._is_jwt_cookie_and_session_user_mismatch(request)
            if is_mismatch and get_setting(ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE):
                raise JwtSessionUserMismatchError(
                    'Failing otherwise successful JWT authentication due to session user mismatch '
                    'with set request user.'
                )

            set_custom_attribute('jwt_auth_result', 'success-cookie')
            return user_and_auth

        except JwtSessionUserMismatchError as exception:
            # Warn against these errors because JWT vs session user should not be happening.
            logger.warning('Failed JWT Authentication due to session user mismatch.')
            # .. custom_attribute_name: jwt_auth_failed
            # .. custom_attribute_description: Includes a summary of the JWT failure exception
            #       for debugging.
            set_custom_attribute('jwt_auth_failed', 'Exception:{}'.format(repr(exception)))
            set_custom_attribute('jwt_auth_result', 'user-mismatch-enforced-failure')
            raise

        except Exception as exception:
            # Errors in production do not need to be logged (as they may be noisy),
            # but debug logging can help quickly resolve issues during development.
            logger.debug('Failed JWT Authentication.', exc_info=exception)

            exception_to_report = _deepest_jwt_exception(exception)
            set_custom_attribute('jwt_auth_failed', 'Exception:{}'.format(repr(exception_to_report)))

            if is_authenticating_with_jwt_cookie:
                # This check also adds monitoring details
                is_user_mismatch = self._is_jwt_cookie_and_session_user_mismatch(request)
                if is_user_mismatch:
                    set_custom_attribute('jwt_auth_result', 'user-mismatch-failure')
                    raise
                set_custom_attribute('jwt_auth_result', 'forgiven-failure')
                return None

            set_custom_attribute('jwt_auth_result', 'failed-auth-header')
            raise

    def authenticate_credentials(self, payload):
        """Get or create an active user with the username contained in the payload."""
        # TODO it would be good to refactor this heavily-nested function.
        # pylint: disable=too-many-nested-blocks
        username = self._get_username_from_payload(payload)
        if username is None:
            raise exceptions.AuthenticationFailed('JWT must include a preferred_username or username claim!')
        try:
            user, __ = get_user_model().objects.get_or_create(username=username)
            attributes_updated = False
            attribute_map = self.get_jwt_claim_attribute_map()
            attributes_to_merge = self.get_jwt_claim_mergeable_attributes()
            for claim, attr in attribute_map.items():
                payload_value = payload.get(claim)

                if attr in attributes_to_merge:
                    # Merge new values that aren't already set in the user dictionary
                    if not payload_value:
                        continue

                    current_value = getattr(user, attr, None)

                    if current_value:
                        for (key, value) in payload_value.items():
                            if key in current_value:
                                if current_value[key] != value:
                                    logger.info(
                                        'Updating attribute %s[%s] for user %s with value %s',
                                        attr,
                                        key,
                                        user.id,
                                        value,
                                    )
                                    current_value[key] = value
                                    attributes_updated = True
                            else:
                                logger.info(
                                    'Adding attribute %s[%s] for user %s with value %s',
                                    attr,
                                    key,
                                    user.id,
                                    value,
                                )
                                current_value[key] = value
                                attributes_updated = True
                    else:
                        logger.info('Updating attribute %s for user %s with value %s', attr, user.id, payload_value)
                        setattr(user, attr, payload_value)
                        attributes_updated = True
                else:
                    if getattr(user, attr) != payload_value and payload_value is not None:
                        logger.info('Updating attribute %s for user %s with value %s', attr, user.id, payload_value)
                        setattr(user, attr, payload_value)
                        attributes_updated = True

            if attributes_updated:
                user.save()
        except Exception as authentication_error:
            msg = f'[edx-drf-extensions] User retrieval failed for username {username}.'
            logger.exception(msg)
            raise exceptions.AuthenticationFailed(msg) from authentication_error

        return user

    def enforce_csrf(self, request):
        """
        Enforce CSRF validation for Jwt cookie authentication.

        Copied from SessionAuthentication.
        See https://github.com/encode/django-rest-framework/blob/3f19e66d9f2569895af6e91455e5cf53b8ce5640/rest_framework/authentication.py#L131-L141  # noqa E501 line too long
        """
        check = CSRFCheck(get_response=lambda request: None)
        # populates request.META['CSRF_COOKIE'], which is used in process_view()
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            # CSRF failed, bail with explicit error message
            raise exceptions.PermissionDenied('CSRF Failed: %s' % reason)

    @classmethod
    def is_authenticating_with_jwt_cookie(cls, request):
        """
        Returns True if authenticating with a JWT cookie, and False otherwise.
        """
        try:
            # If there is a token in the authorization header, it takes precedence in
            # get_token_from_request. This ensures that not only is a JWT cookie found,
            # but that it was actually used for authentication.
            request_token = JSONWebTokenAuthentication.get_token_from_request(request)
            cookie_token = JSONWebTokenAuthentication.get_token_from_cookies(request.COOKIES)
            return cookie_token and (request_token == cookie_token)
        except Exception:  # pylint: disable=broad-exception-caught
            return False

    def _is_jwt_cookie_and_session_user_mismatch(self, request):
        """
        Returns True if JWT cookie and session user do not match, False otherwise.

        Arguments:
            request: The request.

        Other notes:
        - Also adds monitoring details for mismatches.
        - Should only be called for JWT cookies.
        """
        jwt_username, jwt_lms_user_id = self._get_unsafe_jwt_cookie_username_and_lms_user_id(request)

        # add early monitoring for the JWT LMS user_id for observability for a variety of user cases

        # .. custom_attribute_name: jwt_cookie_lms_user_id
        # .. custom_attribute_description: The LMS user_id pulled from the
        #     JWT cookie, or None if the JWT was corrupt and it wasn't found.
        #     Note that the decoding is unsafe, so this isn't just for valid cookies.
        set_custom_attribute('jwt_cookie_lms_user_id', jwt_lms_user_id)

        # If we set the request user in middleware for JWT auth, then we'd actually be checking JWT vs JWT username.
        # Additionally, somehow the setting of request.user and the retrieving of request.user below causes some
        # unknown issue in production-like environments, and this allows us to skip that case.
        if _is_request_user_set_for_jwt_auth():
            return False

        wsgi_request = getattr(request, '_request', request)
        if wsgi_request == request:
            # .. custom_attribute_name: jwt_auth_with_django_request
            # .. custom_attribute_description: There exists custom authentication code in the platform that is
            #      calling JwtAuthentication with a Django request, rather than the expected DRF request. This
            #      custom attribute could be used to track down those usages and find ways to eliminate custom
            #      authentication code that lives outside of this library.
            set_custom_attribute('jwt_auth_with_django_request', True)

        # Get the session-based user from the underlying HttpRequest object.
        # This line taken from DRF SessionAuthentication.
        session_user = getattr(wsgi_request, 'user', None)
        if not session_user:  # pragma: no cover
            return False

        if not session_user.is_authenticated or not session_user.username or session_user.username == jwt_username:
            return False

        # .. custom_attribute_name: jwt_auth_mismatch_session_username
        # .. custom_attribute_description: The session authentication username if it
        #      does not match the JWT cookie username. If there is no session user,
        #      or if it matches the JWT cookie username, this attribute will not be included.
        #      Session authentication may have completed in middleware
        #      before getting to DRF. Although this authentication won't stick,
        #      because it will be replaced by DRF authentication, we record it,
        #      because it sometimes does not match the JWT cookie user.
        set_custom_attribute('jwt_auth_mismatch_session_username', session_user.username)
        # .. custom_attribute_name: jwt_auth_mismatch_jwt_cookie_username
        # .. custom_attribute_description: The JWT cookie username if it
        #      does not match the session authentication username.
        #      See jwt_auth_mismatch_session_username description for more details.
        #      Note that there is a low chance that a corrupt JWT cookie will contain a
        #      username and user id that do not correlate, so we capture the actual username,
        #      even though it is likely redundant to jwt_cookie_lms_user_id. To minimize
        #      the use of PII, this attribute is only captured in the case of a mismatch.
        set_custom_attribute('jwt_auth_mismatch_jwt_cookie_username', jwt_username)

        return True

    def _is_jwt_and_lms_user_email_mismatch(self, request, user):
        """
        Returns True if user email in JWT and email of user do not match, False otherwise.
        Arguments:
            request: The request.
            user: user from user_and_auth
        """
        lms_user_email = getattr(user, 'email', None)

        # This function will check for token in the authorization header and return it
        # otherwise it will return token from JWT cookies.
        token = JSONWebTokenAuthentication.get_token_from_request(request)
        decoded_jwt = configured_jwt_decode_handler(token)
        jwt_user_email = decoded_jwt.get('email', None)

        return lms_user_email != jwt_user_email

    def _get_unsafe_jwt_cookie_username_and_lms_user_id(self, request):
        """
        Returns a tuple of the (username, lms user id) from the JWT cookie, or (None, None) if not found.
        """

        # .. custom_attribute_name: jwt_cookie_unsafe_decode_issue
        # .. custom_attribute_description: Since we are doing an unsafe JWT decode, it should generally work unless
        #     the JWT cookie were tampered with. This attribute will contain the value 'missing-claim' if either the
        #     username or user_id claim is missing, or 'decode-error' if the JWT cookie can't be decoded at all. This
        #     attribute will not exist if there is no issue decoding the cookie.

        try:
            cookie_token = JSONWebTokenAuthentication.get_token_from_cookies(request.COOKIES)
            unsafe_decoded_jwt = unsafe_jwt_decode_handler(cookie_token)
            jwt_username = self._get_username_from_payload(unsafe_decoded_jwt)
            jwt_lms_user_id = unsafe_decoded_jwt.get('user_id', None)
            if not jwt_username or not jwt_lms_user_id:
                set_custom_attribute('jwt_cookie_unsafe_decode_issue', 'missing-claim')
        except Exception:  # pylint: disable=broad-exception-caught
            jwt_username = None
            jwt_lms_user_id = None
            set_custom_attribute('jwt_cookie_unsafe_decode_issue', 'decode-error')

        return (jwt_username, jwt_lms_user_id)

    def _get_username_from_payload(self, payload):
        """
        Returns the username from the payload.

        WARNING:
        1. This doesn't play well with JSONWebTokenAuthentication.jwt_get_username_from_payload, but
        some services do not have JWT_PAYLOAD_GET_USERNAME_HANDLER configured.
        2. It's unclear if `username` is used for any old JWTs, but this could probably be removed.
        """
        return payload.get('preferred_username') or payload.get('username')


_IS_REQUEST_USER_SET_FOR_JWT_AUTH_CACHE_KEY = '_is_request_user_for_jwt_set'


def set_flag_is_request_user_set_for_jwt_auth():
    """
    Sets a flag that the shows the request user was set to be based on JWT auth.

    Used to coordinate between middleware and JwtAuthentication. Note that the flag
    is stored in this module to avoid circular dependencies.
    """
    _get_module_request_cache()[_IS_REQUEST_USER_SET_FOR_JWT_AUTH_CACHE_KEY] = True


def is_jwt_authenticated(request):
    successful_authenticator = getattr(request, 'successful_authenticator', None)
    if not isinstance(successful_authenticator, JSONWebTokenAuthentication):
        return False
    if not getattr(request, 'auth', None):
        logger.error(
            'Unexpected error: Used JwtAuthentication, '
            'but the request auth attribute was not populated with the JWT.'
        )
        return False
    return True


def get_decoded_jwt_from_auth(request):
    """
    Grab jwt from request.auth in request if possible.

    Returns a decoded jwt dict if it can be found.
    Returns None if the jwt is not found.
    """
    if not is_jwt_authenticated(request):
        return None

    return configured_jwt_decode_handler(request.auth)


def _deepest_jwt_exception(exception):
    """
    Given an exception, traverse down the __context__ tree
    until you get to the deepest exceptions which is still
    a subclass of PyJWTError.  If no PyJWTError subclass
    exists, then just return the original exception.
    """
    relevant_exception = exception
    cur_exception = exception

    # An exception always has a context but if it's the deepest
    # exception, than __context__ will return None
    while cur_exception.__context__:
        cur_exception = cur_exception.__context__
        if isinstance(cur_exception, jwt_exceptions.PyJWTError):
            relevant_exception = cur_exception

    return relevant_exception


def _get_module_request_cache():
    return RequestCache(__name__).data


def _is_request_user_set_for_jwt_auth():
    """
    Returns whether the request user was set to be based on JWT auth in JwtAuthCookieMiddleware.

    This is a public method to enable coordination with the JwtAuthentication class.
    """
    return _get_module_request_cache().get(_IS_REQUEST_USER_SET_FOR_JWT_AUTH_CACHE_KEY, False)
