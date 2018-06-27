""" JWT decoder utility functions. """
import logging

import jwt
from semantic_version import Version
from django.conf import settings
from rest_framework_jwt.settings import api_settings

from edx_rest_framework_extensions.settings import get_jwt_issuers

logger = logging.getLogger(__name__)


class JwtTokenVersion(object):
    latest_supported = '1.1.0'

    starting_version = '1.0.0'
    added_version = '1.1.0'
    added_is_restricted = '1.1.0'
    added_filters = '1.1.0'


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
            decoded_token = jwt.decode(
                token,
                jwt_issuer['SECRET_KEY'],
                api_settings.JWT_VERIFY,
                options=options,
                leeway=api_settings.JWT_LEEWAY,
                audience=jwt_issuer['AUDIENCE'],
                issuer=jwt_issuer['ISSUER'],
                algorithms=[api_settings.JWT_ALGORITHM]
            )
            token_version = decode_and_verify_version(decoded_token)
            upgraded_token = _upgrade_token(decoded_token, token_version)
            return upgraded_token
        except jwt.InvalidTokenError:
            msg = "Token decode failed for issuer '{issuer}'".format(issuer=jwt_issuer['ISSUER'])
            logger.info(msg, exc_info=True)

    msg = 'All combinations of JWT issuers and secret keys failed to validate the token.'
    logger.error(msg)
    raise jwt.InvalidTokenError(msg)


def decode_and_verify_version(decoded_token):
    """
    Verify that the JWT version is supported.
    """
    supported_version = Version(
        settings.JWT_AUTH.get('JWT_SUPPORTED_VERSION', JwtTokenVersion.latest_supported)
    )
    jwt_version = Version(
        decoded_token.get('version', JwtTokenVersion.starting_version)
    )
    if jwt_version.major > supported_version.major:
        logger.info('Token decode failed due to unsupported JWT version number [%s]', str(jwt_version))
        raise jwt.InvalidTokenError

    return jwt_version


def decode_jwt_scopes(token):
    """
    Decode the JWT and return the scopes claim.
    """
    return jwt_decode_handler(token).get('scopes', [])


def decode_jwt_is_restricted(token):
    """
    Decode the JWT and return the is_restricted claim.
    """
    return jwt_decode_handler(token)['is_restricted']


def decode_jwt_filters(token):
    """
    Decode the JWT, parse the filters claim, and return a
    list of (filter_type, filter_value) tuples.
    """
    return [jwt_filter.split(':') for jwt_filter in jwt_decode_handler(token)['filters']]


def _upgrade_token(token, token_version):
    """
    Returns an updated token that includes default values for
    fields that were introduced since the token was created
    by checking its version number.
    """
    def _upgrade_version(token, token_version):
        """
        Tokens didn't always contain a version number so we
        default to a nominal starting number.
        """
        token['version'] = token.get('version', str(token_version))

    def _upgrade_is_restricted(token, token_version):
        """
        We can safely default to False since all "restricted" tokens
        created prior to this version were always created as expired
        tokens. Expired tokens would not validate and so would
        not get as this far into the decoding process.
        """
        if token_version < Version(JwtTokenVersion.added_is_restricted):
            token['is_restricted'] = token.get('is_restricted', False)

    def _upgrade_filters(token, token_version):
        """
        We can safely default to an empty list of filters since
        previously created tokens were either "restricted" (always 
        expired) or had full access.
        """
        if token_version < Version(JwtTokenVersion.added_filters):
            token['filters'] = token.get('filters', [])

    _upgrade_version(token, token_version)
    _upgrade_is_restricted(token, token_version)
    _upgrade_filters(token, token_version)
    return token
