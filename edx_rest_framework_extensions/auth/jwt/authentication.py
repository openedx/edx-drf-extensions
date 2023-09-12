""" JWT Authentication class. """

import logging

from django.contrib.auth import get_user_model
from django.middleware.csrf import CsrfViewMiddleware
from edx_django_utils.monitoring import set_custom_attribute
from jwt import exceptions as jwt_exceptions
from rest_framework import exceptions
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from edx_rest_framework_extensions.auth.jwt.decoder import configured_jwt_decode_handler
from edx_rest_framework_extensions.config import ENABLE_FORGIVING_JWT_COOKIES
from edx_rest_framework_extensions.settings import get_setting


logger = logging.getLogger(__name__)


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
        is_forgiving_jwt_cookies_enabled = get_setting(ENABLE_FORGIVING_JWT_COOKIES)
        # .. custom_attribute_name: is_forgiving_jwt_cookies_enabled
        # .. custom_attribute_description: This is temporary custom attribute to show
        #      whether ENABLE_FORGIVING_JWT_COOKIES is toggled on or off.
        #      See docs/decisions/0002-remove-use-jwt-cookie-header.rst
        set_custom_attribute('is_forgiving_jwt_cookies_enabled', is_forgiving_jwt_cookies_enabled)

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

        is_authenticating_with_jwt_cookie = self.is_authenticating_with_jwt_cookie(request)
        try:
            user_and_auth = super().authenticate(request)

            # Unauthenticated, CSRF validation not required
            if not user_and_auth:
                set_custom_attribute('jwt_auth_result', 'n/a')
                return user_and_auth

            # Not using JWT cookie, CSRF validation not required
            if not is_authenticating_with_jwt_cookie:
                set_custom_attribute('jwt_auth_result', 'success-auth-header')
                return user_and_auth

            self.enforce_csrf(request)

            # CSRF passed validation with authenticated user
            set_custom_attribute('jwt_auth_result', 'success-cookie')
            return user_and_auth

        except Exception as exception:
            # Errors in production do not need to be logged (as they may be noisy),
            # but debug logging can help quickly resolve issues during development.
            logger.debug('Failed JWT Authentication,', exc_info=exception)
            # .. custom_attribute_name: jwt_auth_failed
            # .. custom_attribute_description: Includes a summary of the JWT failure exception
            #       for debugging.
            exception_to_report = _deepest_jwt_exception(exception)
            set_custom_attribute('jwt_auth_failed', 'Exception:{}'.format(repr(exception_to_report)))

            is_jwt_failure_forgiven = is_forgiving_jwt_cookies_enabled and is_authenticating_with_jwt_cookie
            if is_jwt_failure_forgiven:
                set_custom_attribute('jwt_auth_result', 'forgiven-failure')
                return None
            if is_authenticating_with_jwt_cookie:
                set_custom_attribute('jwt_auth_result', 'failed-cookie')
            else:
                set_custom_attribute('jwt_auth_result', 'failed-auth-header')
            raise

    def authenticate_credentials(self, payload):
        """Get or create an active user with the username contained in the payload."""
        # TODO it would be good to refactor this heavily-nested function.
        # pylint: disable=too-many-nested-blocks
        username = payload.get('preferred_username') or payload.get('username')
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
