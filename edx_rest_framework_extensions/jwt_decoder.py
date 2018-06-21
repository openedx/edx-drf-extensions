""" JWT decoder utility functions. """
import logging

import jwt
import semantic_version
from django.conf import settings
from rest_framework_jwt.settings import api_settings

from edx_rest_framework_extensions.settings import get_jwt_issuers

DEFAULT_JWT_SUPPORTED_VERSION = '1.0.0'
logger = logging.getLogger(__name__)


def jwt_decode_handler(token):
    """
    Decodes a JSON Web Token (JWT).

    Notes:
        * Requires "exp" and "iat" claims to be present in the token's payload.
        * Supports multiple issuer decoding via settings.JWT_AUTH['JWT_ISSUERS'] (see below)
        * Aids debugging by logging DecodeError and InvalidTokenError log entries when decoding fails.

    Examples:
        Use with `djangorestframework-jwt <https://getblimp.github.io/django-rest-framework-jwt/>`_, by changing
        your Django settings:

        .. code-block:: python

            JWT_AUTH = {
                'JWT_DECODE_HANDLER': 'edx_rest_framework_extensions.jwt_decoder.jwt_decode_handler',
                'JWT_ISSUER': 'https://the.jwt.issuer',
                'JWT_SECRET_KEY': 'the-jwt-secret-key',  (defaults to settings.SECRET_KEY)
                'JWT_AUDIENCE': 'the-jwt-audience',
            }

        Enable multi-issuer support by specifying a list of dictionaries as settings.JWT_AUTH['JWT_ISSUERS']:

        .. code-block:: python

            JWT_ISSUERS = [
                    {
                        'ISSUER': 'test-issuer-1',
                        'SECRET_KEY': 'test-secret-key-1',
                        'AUDIENCE': 'test-audience-1',
                    },
                    {
                        'ISSUER': 'test-issuer-2',
                        'SECRET_KEY': 'test-secret-key-2',
                        'AUDIENCE': 'test-audience-2',
                    }
                ]

    Args:
        token (str): JWT to be decoded.

    Returns:
        dict: Decoded JWT payload.

    Raises:
        MissingRequiredClaimError: Either the exp or iat claims is missing from the JWT payload.
        InvalidTokenError: Decoding fails.
    """

    options = {
        'verify_exp': api_settings.JWT_VERIFY_EXPIRATION,
        'verify_aud': settings.JWT_AUTH.get('JWT_VERIFY_AUDIENCE', True),
        'require_exp': True,
        'require_iat': True,
    }

    for jwt_issuer in get_jwt_issuers():
        try:
            decoded = jwt.decode(
                token,
                jwt_issuer['SECRET_KEY'],
                api_settings.JWT_VERIFY,
                options=options,
                leeway=api_settings.JWT_LEEWAY,
                audience=jwt_issuer['AUDIENCE'],
                issuer=jwt_issuer['ISSUER'],
                algorithms=[api_settings.JWT_ALGORITHM]
            )
            verify_jwt_version(decoded)
            return decoded
        except jwt.InvalidTokenError:
            msg = "Token decode failed for issuer '{issuer}'".format(issuer=jwt_issuer['ISSUER'])
            logger.info(msg, exc_info=True)

    msg = 'All combinations of JWT issuers and secret keys failed to validate the token.'
    logger.error(msg)
    raise jwt.InvalidTokenError(msg)


def verify_jwt_version(decoded_token):
    """
    Verify that the JWT version is supported.
    """
    supported_version = semantic_version.Version(
        settings.JWT_AUTH.get('JWT_SUPPORTED_VERSION', DEFAULT_JWT_SUPPORTED_VERSION)
    )
    jwt_version = semantic_version.Version(
        decoded_token.get('version', str(supported_version))
    )
    if jwt_version.major > supported_version.major:
        logger.info('Token decode failed due to unsupported JWT version number [%s]', str(jwt_version))
        raise jwt.InvalidTokenError


def decode_jwt_scopes(token):
    """
    Decode the JWT and return the scopes claim.
    """
    return jwt_decode_handler(token).get('scopes', [])


def decode_jwt_filters(token):
    """
    Decode the JWT, parse the filters clain, and return a
    list of (provider_type, filter_value) tuples.
    """
    return [jwt_filter.split(':') for jwt_filter in jwt_decode_handler(token).get('filters', [])]
