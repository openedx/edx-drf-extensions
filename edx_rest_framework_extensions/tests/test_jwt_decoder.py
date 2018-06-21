""" Tests for utility functions. """
import copy
from time import time

import ddt
import jwt
import mock
from django.conf import settings
from django.test import override_settings, TestCase

from edx_rest_framework_extensions.tests.factories import UserFactory
from edx_rest_framework_extensions.jwt_decoder import jwt_decode_handler


def generate_jwt(user, scopes=None, filters=None):
    """
    Generate a valid JWT for authenticated requests.
    """
    access_token = generate_jwt_payload(user, scopes=scopes, filters=filters)
    return generate_jwt_token(access_token)


def generate_jwt_token(payload, signing_key=None):
    """
    Generate a valid JWT token for authenticated requests.
    """
    signing_key = signing_key or settings.JWT_AUTH['JWT_ISSUERS'][0]['SECRET_KEY']
    return jwt.encode(payload, signing_key).decode('utf-8')


def generate_jwt_payload(user, scopes=None, filters=None, version='1.0.0'):
    """
    Generate a valid JWT payload given a user and optionally scopes and filters.
    """
    jwt_issuer_data = settings.JWT_AUTH['JWT_ISSUERS'][0]
    now = int(time())
    ttl = 5
    payload = {
        'iss': jwt_issuer_data['ISSUER'],
        'aud': jwt_issuer_data['AUDIENCE'],
        'username': user.username,
        'email': user.email,
        'iat': now,
        'exp': now + ttl,
    }
    if version:
        payload['version'] = version
    if scopes:
        payload['scopes'] = scopes
    if filters:
        payload['filters'] = filters
    return payload


def exclude_from_jwt_auth_setting(key):
    """
    Clone the JWT_AUTH setting dict and remove the given key.
    """
    jwt_auth = copy.deepcopy(settings.JWT_AUTH)
    del jwt_auth[key]
    return jwt_auth


def update_jwt_auth_setting(jwt_auth_overrides):
    """
    Clone the JWT_AUTH setting dict and update it with the given overrides.
    """
    jwt_auth = copy.deepcopy(settings.JWT_AUTH)
    jwt_auth.update(jwt_auth_overrides)
    return jwt_auth


@ddt.ddt
class JWTDecodeHandlerTests(TestCase):
    """ Tests for the `jwt_decode_handler` utility function. """
    def setUp(self):
        super(JWTDecodeHandlerTests, self).setUp()
        self.user = UserFactory()
        self.payload = generate_jwt_payload(self.user)
        self.jwt = generate_jwt_token(self.payload)

    def test_decode_success(self):
        """
        Confirms that the format of the valid response from the token decoder matches the payload
        """
        self.assertDictEqual(jwt_decode_handler(self.jwt), self.payload)

    @ddt.data(*settings.JWT_AUTH['JWT_ISSUERS'])
    def test_decode_valid_token_multiple_valid_issuers(self, jwt_issuer):
        """
        Validates that a valid token is properly decoded given a list of multiple valid issuers
        """

        # Verify that each valid issuer is properly matched against the valid issuers list
        # and used to decode the token that was generated using said valid issuer data
        self.payload['iss'] = jwt_issuer['ISSUER']
        token = generate_jwt_token(self.payload, jwt_issuer['SECRET_KEY'])
        self.assertEqual(jwt_decode_handler(token), self.payload)

    def test_decode_failure(self):
        """
        Verifies the function logs decode failures, and raises an InvalidTokenError if the token cannot be decoded
        """

        # Create tokens using each invalid issuer and attempt to decode them against
        # the valid issuers list, which won't work
        with mock.patch('edx_rest_framework_extensions.jwt_decoder.logger') as patched_log:
            with self.assertRaises(jwt.InvalidTokenError):
                self.payload['iss'] = 'invalid-issuer'
                signing_key = 'invalid-secret-key'
                # Generate a token using the invalid issuer data
                token = generate_jwt_token(self.payload, signing_key)
                # Attempt to decode the token against the entries in the valid issuers list,
                # which will fail with an InvalidTokenError
                jwt_decode_handler(token)

            # Verify that the proper entries were written to the log file
            msg = "Token decode failed for issuer 'test-issuer-1'"
            patched_log.info.assert_any_call(msg, exc_info=True)

            msg = "Token decode failed for issuer 'test-issuer-2'"
            patched_log.info.assert_any_call(msg, exc_info=True)

            msg = "All combinations of JWT issuers and secret keys failed to validate the token."
            patched_log.error.assert_any_call(msg)

    def test_decode_failure_invalid_token(self):
        """
        Verifies the function logs decode failures, and raises an InvalidTokenError if the token cannot be decoded
        """

        # Create tokens using each invalid issuer and attempt to decode them against
        # the valid issuers list, which won't work
        with mock.patch('edx_rest_framework_extensions.jwt_decoder.logger') as patched_log:
            with self.assertRaises(jwt.InvalidTokenError):
                # Attempt to decode an invalid token, which will fail with an InvalidTokenError
                jwt_decode_handler("invalid.token")

            # Verify that the proper entries were written to the log file
            msg = "Token decode failed for issuer 'test-issuer-1'"
            patched_log.info.assert_any_call(msg, exc_info=True)

            msg = "Token decode failed for issuer 'test-issuer-2'"
            patched_log.info.assert_any_call(msg, exc_info=True)

            msg = "All combinations of JWT issuers and secret keys failed to validate the token."
            patched_log.error.assert_any_call(msg)

    @override_settings(JWT_AUTH=exclude_from_jwt_auth_setting('JWT_SUPPORTED_VERSION'))
    def test_decode_supported_jwt_version_not_specified(self):
        """
        Verifies the JWT is decoded successfully when the JWT_SUPPORTED_VERSION setting is not specified.
        """
        token = generate_jwt_token(self.payload)
        self.assertDictEqual(jwt_decode_handler(token), self.payload)

    @ddt.data(None, '0.5.0', '1.0.0', '1.0.5', '1.5.0', '1.5.5')
    def test_decode_supported_jwt_version(self, jwt_version):
        """
        Verifies the JWT is decoded successfully when the JWT_SUPPORTED_VERSION setting is not specified.
        """
        jwt_payload = generate_jwt_payload(self.user, version=jwt_version)
        token = generate_jwt_token(jwt_payload)
        self.assertDictEqual(jwt_decode_handler(token), jwt_payload)

    @override_settings(JWT_AUTH=update_jwt_auth_setting({'JWT_SUPPORTED_VERSION': '0.5.0'}))
    def test_decode_unsupported_jwt_version(self):
        """
        Verifies the function logs decode failures, and raises an
        InvalidTokenError if the token version is not supported.
        """
        with mock.patch('edx_rest_framework_extensions.jwt_decoder.logger') as patched_log:
            with self.assertRaises(jwt.InvalidTokenError):
                token = generate_jwt_token(self.payload)
                jwt_decode_handler(token)

            # Verify that the proper entries were written to the log file
            msg = "Token decode failed due to unsupported JWT version number [%s]"
            patched_log.info.assert_any_call(msg, '1.0.0')

            msg = "Token decode failed for issuer 'test-issuer-1'"
            patched_log.info.assert_any_call(msg, exc_info=True)

            msg = "Token decode failed for issuer 'test-issuer-2'"
            patched_log.info.assert_any_call(msg, exc_info=True)

            msg = "All combinations of JWT issuers and secret keys failed to validate the token."
            patched_log.error.assert_any_call(msg)
