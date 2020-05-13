""" JWT Authentication class. """

import logging

from django.contrib.auth import get_user_model
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.encoding import force_str
from edx_django_utils.monitoring import set_custom_attribute
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_jwt.blacklist.exceptions import InvalidAuthorizationCredentials

from edx_rest_framework_extensions.auth.jwt.decoder import configured_jwt_decode_handler
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
        is_jwt_from_authorization_header = self._is_jwt_from_authorization_header(request)

        try:
            user_and_auth = super().authenticate(request)

            # Unable to authenticate, proceed to next Authentication class
            if not user_and_auth:
                return None

            # JWT found in authorization header, CSRF validation not required
            if is_jwt_from_authorization_header:
                return user_and_auth

            # TODO: Why do we need CSRF protection but the original class does not?
            # Enforce CSRF for JWT Cookie (assumed if not using the authorization header)
            self.enforce_csrf(request)

            # CSRF passed validation with authenticated user
            return user_and_auth

        except (AuthenticationFailed, PermissionDenied) as exception:
            if is_jwt_from_authorization_header:
                logger.debug('Invalid JWT auth header.', exc_info=exception)
                set_custom_attribute('jwt_auth_failed', 'auth header:{}'.format(repr(exception)))
                raise

            # TODO: Add test coverage
            # If we reach here, we must be using the JWT Cookie.
            # For failed authentication using JWT Cookie, we will allow other Authentication classes
            # to have a chance to attempt authentication by returning none, but will log and add monitoring.
            logger.debug('Invalid JWT Cookie. Proceeding to next Authentication class.', exc_info=exception)
            set_custom_attribute('jwt_auth_failed', 'cookie:{}'.format(repr(exception)))
            return None

    @classmethod
    def _is_jwt_from_authorization_header(cls, request):
        """
        Returns True if the JWT is from the authorization header, and False otherwise (i.e. not found or JWT cookie)

        This is a modified version of JSONWebTokenAuthentication.get_token_from_request:
            https://github.com/Styria-Digital/django-rest-framework-jwt/blob/88096b16d8639336fcb34d1e3420fafd1dc7c8f7/src/rest_framework_jwt/authentication.py#L93-L100
        """
        try:
            authorization_header = force_str(get_authorization_header(request))
            jwt_token = cls.get_token_from_authorization_header(authorization_header)
            return bool(jwt_token)
        except (InvalidAuthorizationCredentials, UnicodeDecodeError):
            return False

    def authenticate_credentials(self, payload):
        """Get or create an active user with the username contained in the payload."""
        # TODO it would be good to refactor this heavily-nested function.
        # pylint: disable=too-many-nested-blocks
        username = payload.get('preferred_username') or payload.get('username')
        if username is None:
            raise AuthenticationFailed('JWT must include a preferred_username or username claim!')
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
            msg = 'User retrieval failed.'
            logger.exception(msg)
            raise AuthenticationFailed(msg) from authentication_error

        return user

    def enforce_csrf(self, request):
        """
        Enforce CSRF validation for Jwt cookie authentication.

        Copied from SessionAuthentication.
        See https://github.com/encode/django-rest-framework/blob/3f19e66d9f2569895af6e91455e5cf53b8ce5640/rest_framework/authentication.py#L131-L141  # noqa E501 line too long
        """
        check = CSRFCheck()
        # populates request.META['CSRF_COOKIE'], which is used in process_view()
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            # CSRF failed, bail with explicit error message
            raise PermissionDenied('CSRF Failed: %s' % reason)


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
