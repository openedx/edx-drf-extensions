""" JWT Authentication class. """

import logging

import requests
from django.contrib.auth import get_user_model
from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header, BaseAuthentication
from rest_framework_jwt.authentication import JSONWebTokenAuthentication, BaseJSONWebTokenAuthentication

from edx_rest_framework_extensions.exceptions import UserInfoRetrievalFailed
from edx_rest_framework_extensions.settings import get_setting

logger = logging.getLogger(__name__)


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
