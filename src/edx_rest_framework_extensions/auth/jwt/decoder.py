"""
JWT decoder utility functions.

In most of this module, "decode" refers to both verifying and unpacking a JWT,
as a unified operation. (Reading the contents of an unverified JWT would be
a security risk in the general case.)
"""
import logging
import sys

import jwt
from django.conf import settings
from edx_django_utils.monitoring import set_custom_attribute
from jwt.api_jwk import PyJWK, PyJWKSet
from jwt.utils import base64url_encode
from rest_framework_jwt.settings import api_settings
from semantic_version import Version

from edx_rest_framework_extensions.settings import get_first_jwt_issuer, get_jwt_issuers


logger = logging.getLogger(__name__)


class JwtTokenVersion:
    default_latest_supported = '1.2.0'

    starting_version = '1.0.0'
    added_version = '1.1.0'


def jwt_decode_handler(token, decode_symmetric_token=True):
    """
    Decodes (and verifies) a JSON Web Token (JWT).

    Notes:
        * Requires "exp" and "iat" claims to be present in the token's payload.
        * Aids debugging by logging InvalidTokenError log entries when decoding fails.
        * Setting for JWT_DECODE_HANDLER expects a single argument, token. The argument decode_symmetric_token
          is for internal use only.

    Examples:
        Use with `djangorestframework-jwt <https://getblimp.github.io/django-rest-framework-jwt/>`_, by changing
        your Django settings:

        .. code-block:: python

            JWT_AUTH = {
                'JWT_DECODE_HANDLER': 'edx_rest_framework_extensions.auth.jwt.decoder.jwt_decode_handler',
                'JWT_ISSUER': 'https://the.jwt.issuer',
                'JWT_SECRET_KEY': 'the-jwt-secret-key',  (defaults to settings.SECRET_KEY)
                'JWT_AUDIENCE': 'the-jwt-audience',
                'JWT_PUBLIC_SIGNING_JWK_SET': 'the-jwk-set-of-public-signing-keys',
            }

    Warning:
        Do **not** use this method internally.  Only use it in ``JWT_DECODE_HANDLER`` like the above example.
        Internally, use ``configured_jwt_decode_handler`` which respects the ``JWT_DECODE_HANDLER`` setting.

    Args:
        token (str): JWT to be decoded.
        decode_symmetric_token (bool): Whether to decode symmetric tokens or not. Pass False for asymmetric tokens only

    Returns:
        dict: Decoded JWT payload.

    Raises:
        MissingRequiredClaimError: Either the exp or iat claims is missing from the JWT payload.
        InvalidTokenError: Decoding fails.
    """
    jwt_issuer = get_first_jwt_issuer()
    _verify_jwt_signature(token, jwt_issuer, decode_symmetric_token=decode_symmetric_token)
    decoded_token = _decode_and_verify_token(token, jwt_issuer)
    return _set_token_defaults(decoded_token)


def unsafe_jwt_decode_handler(token):
    """
    Decodes a JSON Web Token (JWT) with NO verification.

    Args:
        token (str): JWT to be decoded.

    Returns:
        dict: Decoded JWT payload

    Raises:
        InvalidTokenError: Decoding fails.
    """
    decoded_token = _unsafe_decode_token_with_no_verification(token)
    return _set_token_defaults(decoded_token)


def configured_jwt_decode_handler(token):
    """
    Calls the ``jwt_decode_handler`` configured in the ``JWT_DECODE_HANDLER`` setting.
    """
    api_setting_jwt_decode_handler = api_settings.JWT_DECODE_HANDLER
    return api_setting_jwt_decode_handler(token)


def get_asymmetric_only_jwt_decode_handler(token):
    """
    Returns a jwt_decode_handler that will only validate asymmetrically signed JWTs.

    WARNING: This will only work with a service that is configured to use the
       jwt_decode_handler from this library. This can be used to decode an
       already decoded JWT, to ensure it is asymmetrically signed. This check
       can go away once the DEPR for symmetrically signed JWTs is complete:
       https://github.com/openedx/public-engineering/issues/83
    """
    return jwt_decode_handler(token, decode_symmetric_token=False)


def decode_jwt_scopes(token):
    """
    Decode the JWT and return the scopes claim.
    """
    return configured_jwt_decode_handler(token).get('scopes', [])


def decode_jwt_is_restricted(token):
    """
    Decode the JWT and return the is_restricted claim.
    """
    return configured_jwt_decode_handler(token).get('is_restricted', False)


def decode_jwt_filters(token):
    """
    Decode the JWT, parse the filters claim, and return a
    list of (filter_type, filter_value) tuples.
    """
    return [
        jwt_filter.split(':')
        for jwt_filter in configured_jwt_decode_handler(token).get('filters', [])
    ]


def _set_token_defaults(token):
    """
    Returns an updated token that includes default values for
    fields that were introduced since the token was created
    by checking its version number.
    """
    def _verify_version(jwt_version):
        supported_version = Version(
            settings.JWT_AUTH.get('JWT_SUPPORTED_VERSION', JwtTokenVersion.default_latest_supported)
        )
        if jwt_version.major > supported_version.major:
            logger.info('Token decode failed due to unsupported JWT version number [%s]', str(jwt_version))
            raise jwt.InvalidTokenError('JWT version number [%s] is unsupported' % str(jwt_version))

    def _get_and_set_version(token):
        """
        Tokens didn't always contain a version number so we
        default to a nominal starting number.
        """
        if 'version' not in token:
            token['version'] = str(JwtTokenVersion.starting_version)

        return Version(token['version'])

    def _set_is_restricted(token):
        """
        We can safely default to False since all "restricted" tokens
        created prior to the addition of the `is_restricted` flag were
        always created as expired tokens. Expired tokens would not
        validate and so would not get this far into the decoding process.
        # TODO: ARCH-166
        """
        if 'is_restricted' not in token:
            token['is_restricted'] = False

    def _set_filters(token):
        """
        We can safely default to an empty list of filters since
        previously created tokens were either "restricted" (always
        expired) or had full access.
        # TODO: ARCH-166
        """
        if 'filters' not in token:
            token['filters'] = []

    token_version = _get_and_set_version(token)
    _verify_version(token_version)
    _set_is_restricted(token)
    _set_filters(token)
    return token


def _verify_jwt_signature(token, jwt_issuer, decode_symmetric_token):
    """
    Verifies the JWT signature. Raises InvalidTokenError in the event of an error.

    Arguments:
        token (str): JWT to be decoded.
        jwt_issuer (dict): A dict of JWT issuer related settings, containing the symmetric key.
        decode_symmetric_token (bool): Whether to decode symmetric tokens or not. Pass False for asymmetric tokens only
    """
    # .. custom_attribute_name: jwt_auth_check_symmetric_key
    # .. custom_attribute_description: True if symmetric keys will also be used for checking
    #   the JWT signature, and False if only asymmetric keys will be used.
    set_custom_attribute('jwt_auth_check_symmetric_key', decode_symmetric_token)

    # For observability purposes, we will first try asymmetric keys only to verify
    #   that we no longer need the symmetric key. However, if this fails, we will
    #   continue on to the original code path and try all keys (including symmetric)
    #   and add monitoring to let us know. This is meant to be temporary, until we
    #   can fully retire code paths for symmetric keys, as part of
    #   DEPR: Symmetric JWTs: https://github.com/openedx/public-engineering/issues/83

    # Pass only asymmetric_keys to only include asymmetric keys at first
    asymmetric_keys = settings.JWT_AUTH.get('JWT_PUBLIC_SIGNING_JWK_SET')
    key_set = get_verification_jwk_key_set(asymmetric_keys=asymmetric_keys)
    # .. custom_attribute_name: jwt_auth_verify_asymmetric_keys_count
    # .. custom_attribute_description: Number of JWT verification keys in use for this
    #   verification. Should be same as number of asymmetric public keys. This is
    #   intended to aid in key rotations; once the average count stabilizes at a
    #   higher number after adding a public key, it should be safe to change the secret key.
    set_custom_attribute('jwt_auth_verify_asymmetric_keys_count', len(key_set))

    try:
        verify_jwk_signature_using_keyset(token, key_set, aud=jwt_issuer['AUDIENCE'])
        # .. custom_attribute_name: jwt_auth_asymmetric_verified
        # .. custom_attribute_description: Whether the JWT was successfully verified
        #   using an asymmetric key.
        set_custom_attribute('jwt_auth_asymmetric_verified', True)
        return
    except Exception:  # pylint: disable=broad-except
        # Continue to the old code path of trying all keys
        pass

    # The following is the original code that includes both the symmetric and asymmetric keys
    #   as requested with the decode_symmetric_token argument. Note that the check against
    #   the asymmetric keys here is redundant and unnecessary, but this code is temporary and
    #   will be simplified once symmetric keys have been fully retired.

    secret_key = jwt_issuer['SECRET_KEY'] if decode_symmetric_token else None
    key_set = get_verification_jwk_key_set(asymmetric_keys=asymmetric_keys, secret_key=secret_key)
    # .. custom_attribute_name: jwt_auth_verify_all_keys_count
    # .. custom_attribute_description: Number of JWT verification keys in use for this
    #   verification. Should be same as number of asymmetric public keys, plus one if
    #   a symmetric key secret is set. This is intended to aid in key rotations; once
    #   the average count stabilizes at a higher number after adding a public key, it
    #   should be safe to change the secret key.
    set_custom_attribute('jwt_auth_verify_all_keys_count', len(key_set))

    try:
        verify_jwk_signature_using_keyset(token, key_set, aud=jwt_issuer['AUDIENCE'])
        # .. custom_attribute_name: jwt_auth_symmetric_verified
        # .. custom_attribute_description: Whether the JWT was successfully verified
        #   using a symmetric key.
        # Note: Rather than using a single custom attribute like ``jwt_auth_verified``
        #   with values of 'symmetric' or 'asymmetric', we use two separate custom
        #   attribute names (e.g. jwt_auth_symmetric_verified and jwt_auth_asymmetric_verified),
        #   so that if each of these were set separately in the same request, they
        #   wouldn't clobber each other.
        set_custom_attribute('jwt_auth_symmetric_verified', True)
        return
    except Exception as token_error:
        # .. custom_attribute_name: jwt_auth_verification_failed
        # .. custom_attribute_description: True if the JWT token verification failed.
        set_custom_attribute('jwt_auth_verification_failed', True)
        logger.exception('Token verification failed.')
        exc_info = sys.exc_info()
        raise jwt.InvalidTokenError(exc_info[2]) from token_error


def verify_jwk_signature_using_keyset(token, key_set, aud=None, iss=None, verify_signature=True, verify_exp=True):
    """
    Verifies the signature of a JSON Web Token (JWT) using a provided JSON Web Key (PyJWK) key set.

    Args:
        token (str): The JWT to be verified.
        key_set (list -> PyJWK): A list containing PyJWKs (JSON Web Keys)
            for signature verification.
        aud (str or None): The expected "aud" (audience) claim in the JWT.
            If provided, the JWT's "aud" claim must match this value for
            the verification to succeed.
        iss (str or None): The expected "iss" (issuer) claim in the JWT.
            If provided, the JWT's "iss" claim must match this value for
            the verification to succeed.
        verify_signature (bool): Whether to verify the JWT's digital signature.
            Set to False if you want to skip signature verification
            (e.g., if the JWT is already pre-verified).
        verify_exp (bool): Whether to verify the JWT's expiration time ("exp" claim).
            Set to False if you want to skip expiration time verification.

    Returns:
        data (dict): Decoded JWT.

    Raises:
        ValueError: If the token is not a valid JWT or if the key_set is empty
            or improperly formatted.
        jwt.ExpiredSignatureError: If the JWT has expired and verify_exp
            is set to True.
        jwt.InvalidIssuerError: If the "iss" claim does not match the expected
            issuer and iss is provided.
        jwt.InvalidAudienceError: If the "aud" claim does not match the expected
            audience and aud is provided.
        jwt.DecodeError: If the JWT decoding fails for any reason.
    """
    options = {
        'verify_signature': verify_signature,
        'verify_exp': verify_exp,
        'verify_aud': bool(aud),
        'verify_iss': bool(iss)
    }
    data = None

    for i in range(0, len(key_set)):
        try:
            algorithms = None
            if key_set[i].key_type == 'RSA':
                algorithms = ['RS256', 'RS512',]
            elif key_set[i].key_type == 'oct':
                algorithms = ['HS256',]

            data = jwt.decode(
                    token,
                    key=key_set[i].key,
                    algorithms=algorithms,
                    issuer=iss,
                    audience=aud,
                    options=options
                )
            break
        except Exception:  # pylint: disable=broad-except
            if i == len(key_set) - 1:
                raise
    return data


def _decode_and_verify_token(token, jwt_issuer):
    """
    Part of the verification implementation; must not be used in isolation,
    as the signature is actually checked in a different function.
    """
    options = {
        'require': ["exp", "iat"],

        'verify_exp': api_settings.JWT_VERIFY_EXPIRATION,
        'verify_aud': settings.JWT_AUTH.get('JWT_VERIFY_AUDIENCE', True),
        # See https://github.com/openedx/edx-drf-extensions/issues/327 for removing manual issuer verification.
        'verify_iss': False,  # Verified manually below
        'verify_signature': False,  # Verified with JWS already
    }

    decoded_token = jwt.decode(
        token,
        jwt_issuer['SECRET_KEY'],
        options=options,
        leeway=api_settings.JWT_LEEWAY,
        audience=jwt_issuer['AUDIENCE'],
        issuer=jwt_issuer['ISSUER'],
        algorithms=[api_settings.JWT_ALGORITHM],
    )

    # See https://github.com/openedx/edx-drf-extensions/issues/327 for removing this manual issuer validation.
    token_issuer = decoded_token.get('iss')
    # .. custom_attribute_name: jwt_auth_issuer
    # .. custom_attribute_description: Value set to the JWT auth issuer.
    set_custom_attribute('jwt_auth_issuer', token_issuer)
    issuer_matched = any(issuer['ISSUER'] == token_issuer for issuer in get_jwt_issuers())
    if token_issuer == jwt_issuer['ISSUER']:
        # .. custom_attribute_name: jwt_auth_issuer_verification
        # .. custom_attribute_description: Depending on issuer verification, the value will
        #   be one of: matches-first-issuer, matches-later-issuer, or no-match.
        set_custom_attribute('jwt_auth_issuer_verification', 'matches-first-issuer')
    elif issuer_matched:
        set_custom_attribute('jwt_auth_issuer_verification', 'matches-later-issuer')
    else:
        set_custom_attribute('jwt_auth_issuer_verification', 'no-match')
        logger.info('Token decode failed due to mismatched issuer [%s]', token_issuer)
        raise jwt.InvalidTokenError('%s is not a valid issuer.' % token_issuer)

    return decoded_token


def _unsafe_decode_token_with_no_verification(token):
    """
    Returns a decoded JWT token with no verification.
    """
    options = {
        'verify_exp': False,
        'verify_aud': False,
        'verify_iss': False,
        'verify_signature': False,
    }
    decoded_token = jwt.decode(token, options=options)
    return decoded_token


def get_verification_jwk_key_set(asymmetric_keys=None, secret_key=None):
    """
    Creates a JWK Keyset containing the provided keys.

    Args:
        asymmetric_keys (list or None): List of asymmetric JWK verification keys,
            each in JSON format.
        secret_key (str or None): Secret key for symmetric JWT verification, as an
            unencoded string.
    """
    key_set = []

    if asymmetric_keys:
        key_set.extend(PyJWKSet.from_json(asymmetric_keys).keys)

    if secret_key:
        # symmetric key
        encoded_secret_key = base64url_encode(secret_key.encode('utf-8'))
        key_set.append(PyJWK({'k': encoded_secret_key, 'kty': 'oct'}))

    return key_set
