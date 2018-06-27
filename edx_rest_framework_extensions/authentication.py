""" Authentication classes. """

import logging

import requests
from django.contrib.auth import get_user_model
from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header, BaseAuthentication
from rest_framework_jwt.authentication import JSONWebTokenAuthentication, BaseJSONWebTokenAuthentication

from edx_rest_framework_extensions.exceptions import UserInfoRetrievalFailed
from edx_rest_framework_extensions.settings import get_setting

logger = logging.getLogger(__name__)


class BearerAuthentication(BaseAuthentication):
    """
    Simple token based authentication.

    This authentication class is useful for authenticating an OAuth2 access token against a remote
    authentication provider. Clients should authenticate by passing the token key in the "Authorization" HTTP header,
    prepended with the string `"Bearer "`.

    This class relies on the OAUTH2_USER_INFO_URL being set to the value of an endpoint on the OAuth provider, that
    returns a JSON object with information about the user. See ``process_user_info_response`` for the expected format
    of this object. This data will be used to get, or create, a ``User``. Additionally, it is assumed that a successful
    response from this endpoint (authenticated with the provided access token) implies the access token is valid.

    Example Header:
        Authorization: Bearer 401f7ac837da42b97f613d789819ff93537bee6a
    """

    def get_user_info_url(self):
        """ Returns the URL, hosted by the OAuth2 provider, from which user information can be pulled. """
        return get_setting('OAUTH2_USER_INFO_URL')

    def authenticate(self, request):
        if not self.get_user_info_url():
            logger.warning('The setting OAUTH2_USER_INFO_URL is invalid!')
            return None

        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'bearer':
            return None

        if len(auth) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')
        elif len(auth) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        return self.authenticate_credentials(auth[1].decode('utf8'))

    def authenticate_credentials(self, token):
        """
        Validate the bearer token against the OAuth provider.

        Arguments:
            token (str): Access token to validate

        Returns:
            (tuple): tuple containing:

                user (User): User associated with the access token
                access_token (str): Access token

        Raises:
            AuthenticationFailed: The user is inactive, or retrieval of user info failed.
        """

        try:
            user_info = self.get_user_info(token)
        except UserInfoRetrievalFailed:
            msg = 'Failed to retrieve user info. Unable to authenticate.'
            logger.error(msg)
            raise exceptions.AuthenticationFailed(msg)

        user, __ = get_user_model().objects.get_or_create(username=user_info['username'], defaults=user_info)

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        return user, token

    def get_user_info(self, token):
        """
        Retrieves the user info from the OAuth provider.

        Arguments:
            token (str): OAuth2 access token.

        Returns:
            dict

        Raises:
            UserInfoRetrievalFailed: Retrieval of user info from the remote server failed.
        """

        url = self.get_user_info_url()

        try:
            headers = {'Authorization': 'Bearer {}'.format(token)}
            response = requests.get(url, headers=headers)
        except requests.RequestException:
            logger.exception('Failed to retrieve user info due to a request exception.')
            raise UserInfoRetrievalFailed

        if response.status_code == 200:
            return self.process_user_info_response(response.json())
        else:
            msg = 'Failed to retrieve user info. Server [{server}] responded with status [{status}].'.format(
                server=url,
                status=response.status_code
            )
            raise UserInfoRetrievalFailed(msg)

    def process_user_info_response(self, response):
        """
        Process the user info response data.

        By default, this simply maps the edX user info key-values (example below) to Django-friendly names. If your
        provider returns different fields, you should sub-class this class and override this method.

        .. code-block:: python

            {
                "username": "jdoe",
                "email": "jdoe@example.com",
                "first_name": "Jane",
                "last_name": "Doe"
            }

        Arguments:
            response (dict): User info data

        Returns:
            dict
        """
        mapping = (
            ('username', 'preferred_username'),
            ('email', 'email'),
            ('last_name', 'family_name'),
            ('first_name', 'given_name'),
        )

        return {dest: response[source] for dest, source in mapping}

    def authenticate_header(self, request):
        return 'Bearer'


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

    def authenticate(self, request):
        try:
            return super(JwtAuthentication, self).authenticate(request)
        except Exception as ex:
            # Errors in production do not need to be logged (as they may be noisy),
            # but debug logging can help quickly resolve issues during development.
            logger.debug(ex)
            raise

    def authenticate_credentials(self, payload):
        """Get or create an active user with the username contained in the payload."""
        username = payload.get('preferred_username') or payload.get('username')

        if username is None:
            raise exceptions.AuthenticationFailed('JWT must include a preferred_username or username claim!')
        else:
            try:
                user, __ = get_user_model().objects.get_or_create(username=username)
                attributes_updated = False
                for claim, attr in self.get_jwt_claim_attribute_map().items():
                    payload_value = payload.get(claim)

                    if getattr(user, attr) != payload_value and payload_value is not None:
                        setattr(user, attr, payload_value)
                        attributes_updated = True

                if attributes_updated:
                    user.save()
            except:
                msg = 'User retrieval failed.'
                logger.exception(msg)
                raise exceptions.AuthenticationFailed(msg)

        return user


def is_jwt_authenticated(request):
    is_jwt_authenticated = issubclass(
        type(request.successful_authenticator),
        BaseJSONWebTokenAuthentication,
    )
    if is_jwt_authenticated:
        if not getattr(request, 'auth', None):
            logger.error(
                'Unexpected error: Used JwtAuthentication, but the request auth attribute was not populated with the JWT.'
            )
            return False
    return is_jwt_authenticated
