""" Utility functions for tests. """
from time import time

import jwt
from django.conf import settings
from jwt.api_jwk import PyJWK


def generate_jwt(user, scopes=None, filters=None, is_restricted=None):
    """
    Generate a valid JWT for authenticated requests.
    """
    access_token = generate_latest_version_payload(
        user,
        scopes=scopes,
        filters=filters,
        is_restricted=is_restricted
    )
    return generate_jwt_token(access_token)


def generate_jwt_token(payload, signing_key=None):
    """
    Generate a valid JWT token for authenticated requests.
    """
    signing_key = signing_key or settings.JWT_AUTH['JWT_ISSUERS'][0]['SECRET_KEY']
    return jwt.encode(payload, signing_key)


def generate_asymmetric_jwt_token(payload):
    """
    Generate a valid asymmetric JWT token for authenticated requests.
    """
    private_key = PyJWK.from_json(settings.JWT_AUTH['JWT_PRIVATE_SIGNING_JWK'])
    algorithm = settings.JWT_AUTH['JWT_SIGNING_ALGORITHM']
    return jwt.encode(payload, key=private_key.key, algorithm=algorithm)


def generate_latest_version_payload(user, scopes=None, filters=None, version=None,
                                    is_restricted=None):
    """
    Generate a valid JWT payload given a user and optionally scopes and filters.
    """
    payload = generate_unversioned_payload(user)
    payload.update({
        # fix this version and add newly introduced fields as the version updates.
        'version': '1.1.0',
        'filters': [],
        'is_restricted': False,
    })
    if scopes is not None:
        payload['scopes'] = scopes
    if version is not None:
        payload['version'] = version
    if filters is not None:
        payload['filters'] = filters
    if is_restricted is not None:
        payload['is_restricted'] = is_restricted
    return payload


def generate_unversioned_payload(user):
    """
    Generate an unversioned valid JWT payload given a user.

    WARNING: This test utility is mocking JWT creation of the identity service (LMS).
    - A safer alternative might be to move the LMS's JWT creation code to this library.
    """
    jwt_issuer_data = settings.JWT_AUTH['JWT_ISSUERS'][0]
    now = int(time())
    ttl = 600
    payload = {
        'iss': jwt_issuer_data['ISSUER'],
        'aud': jwt_issuer_data['AUDIENCE'],
        'preferred_username': user.username,  # preferred_username is used by Open edX JWTs.
        # WARNING: This `user_id` implementation could lead to bugs because `user_id` should be
        #   conditionally added based on scope, and should not always be available.
        'user_id': user.id,
        'email': user.email,
        'iat': now,
        'exp': now + ttl,
        'scopes': [],
    }
    return payload
