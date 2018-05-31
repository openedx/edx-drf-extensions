""" Tests for utility functions. """
from time import time

import ddt
import jwt
import mock
from django.conf import settings
from django.test import TestCase, override_settings

from edx_rest_framework_extensions.tests.factories import UserFactory
from edx_rest_framework_extensions import utils


def generate_jwt_token(payload, signing_key=None):
    """
    Generate a valid JWT token for authenticated requests.
    """
    signing_key = signing_key or settings.JWT_AUTH['JWT_ISSUERS'][0]['SECRET_KEY']
    return jwt.encode(payload, signing_key).decode('utf-8')


def generate_jwt_payload(user):
    """
    Generate a valid JWT payload given a user.
    """
    jwt_issuer_data = settings.JWT_AUTH['JWT_ISSUERS'][0]
    now = int(time())
    ttl = 5
    return {
        'iss': jwt_issuer_data['ISSUER'],
        'aud': jwt_issuer_data['AUDIENCE'],
        'username': user.username,
        'email': user.email,
        'iat': now,
        'exp': now + ttl
    }


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
        self.assertDictEqual(utils.jwt_decode_handler(self.jwt), self.payload)

    @ddt.data(*settings.JWT_AUTH['JWT_ISSUERS'])
    def test_decode_valid_token_multiple_valid_issuers(self, jwt_issuer):
        """
        Validates that a valid token is properly decoded given a list of multiple valid issuers
        """

        # Verify that each valid issuer is properly matched against the valid issuers list
        # and used to decode the token that was generated using said valid issuer data
        self.payload['iss'] = jwt_issuer['ISSUER']
        token = generate_jwt_token(self.payload, jwt_issuer['SECRET_KEY'])
        self.assertEqual(utils.jwt_decode_handler(token), self.payload)

    def test_decode_failure(self):
        """
        Verifies the function logs decode failures, and raises an InvalidTokenError if the token cannot be decoded
        """

        # Create tokens using each invalid issuer and attempt to decode them against
        # the valid issuers list, which won't work
        with mock.patch('edx_rest_framework_extensions.utils.logger') as patched_log:
            with self.assertRaises(jwt.InvalidTokenError):
                self.payload['iss'] = 'invalid-issuer'
                signing_key = 'invalid-secret-key'
                # Generate a token using the invalid issuer data
                token = generate_jwt_token(self.payload, signing_key)
                # Attempt to decode the token against the entries in the valid issuers list,
                # which will fail with an InvalidTokenError
                utils.jwt_decode_handler(token)

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
        with mock.patch('edx_rest_framework_extensions.utils.logger') as patched_log:
            with self.assertRaises(jwt.InvalidTokenError):
                # Attempt to decode an invalid token, which will fail with an InvalidTokenError
                utils.jwt_decode_handler("invalid.token")

            # Verify that the proper entries were written to the log file
            msg = "Token decode failed for issuer 'test-issuer-1'"
            patched_log.info.assert_any_call(msg, exc_info=True)

            msg = "Token decode failed for issuer 'test-issuer-2'"
            patched_log.info.assert_any_call(msg, exc_info=True)

            msg = "All combinations of JWT issuers and secret keys failed to validate the token."
            patched_log.error.assert_any_call(msg)


@ddt.ddt
class IsTokenVersionIncompatibleTests(TestCase):
    """ Tests for the `is_token_version_incompatible` utility function. """
    def setUp(self):
        super(IsTokenVersionIncompatibleTests, self).setUp()
        self.user = UserFactory()
        self.payload = generate_jwt_payload(self.user)
        self.jwt = generate_jwt_token(self.payload)
        self.decoded_token = utils.jwt_decode_handler(self.jwt)

    def test_token_version_incompatible(self):
        self.decoded_token['version'] = 2
        self.assertTrue(utils.is_token_version_incompatible(self.decoded_token['version']))

    @override_settings(FEATURES={'OAUTH_TOKEN_VERSION': 2})
    def test_token_version_compatible(self):
        self.decoded_token['version'] = 1
        self.assertFalse(utils.is_token_version_incompatible(self.decoded_token['version']))
