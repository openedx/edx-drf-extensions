"""
Unit tests for jwt cookies module.
"""
from unittest import mock

import ddt
from django.http import HttpRequest
from django.test import TestCase, override_settings

from edx_rest_framework_extensions.auth.jwt.decoder import jwt_decode_handler
from edx_rest_framework_extensions.auth.jwt.tests.utils import (
    generate_jwt_token,
    generate_latest_version_payload,
)
from edx_rest_framework_extensions.tests.factories import UserFactory

from .. import cookies


@ddt.ddt
class TestJwtAuthCookies(TestCase):
    @ddt.data(
        (cookies.jwt_cookie_name, 'JWT_AUTH_COOKIE', 'custom-jwt-cookie-name'),
        (cookies.jwt_cookie_header_payload_name, 'JWT_AUTH_COOKIE_HEADER_PAYLOAD', 'custom-jwt-header-payload-name'),
        (cookies.jwt_cookie_signature_name, 'JWT_AUTH_COOKIE_SIGNATURE', 'custom-jwt-signature-name'),
    )
    @ddt.unpack
    def test_get_setting_value(self, jwt_cookie_func, setting_name, setting_value):
        with override_settings(JWT_AUTH={setting_name: setting_value}):
            self.assertEqual(jwt_cookie_func(), setting_value)

    @ddt.data(
        (cookies.jwt_cookie_name, 'edx-jwt-cookie'),
        (cookies.jwt_cookie_header_payload_name, 'edx-jwt-cookie-header-payload'),
        (cookies.jwt_cookie_signature_name, 'edx-jwt-cookie-signature'),
    )
    @ddt.unpack
    def test_get_default_value(self, jwt_cookie_func, expected_default_value):
        self.assertEqual(jwt_cookie_func(), expected_default_value)

    @mock.patch('edx_rest_framework_extensions.auth.jwt.cookies.get_decoded_jwt_from_auth', return_value='decoded.jwt')
    def test_get_decoded_jwt_from_decoded_jwt_from_auth(self, _):
        """Ensure get_decoded_jwt_from_auth is used as part of get_decoded_jwt."""
        decoded_jwt = cookies.get_decoded_jwt(None)

        self.assertEqual('decoded.jwt', decoded_jwt)

    def test_get_decoded_jwt_from_existing_cookie(self):
        user = UserFactory()
        payload = generate_latest_version_payload(user)
        jwt = generate_jwt_token(payload)
        expected_decoded_jwt = jwt_decode_handler(jwt)

        mock_request_with_cookie = mock.Mock(COOKIES={'edx-jwt-cookie': jwt})
        mock_request_with_cookie.__class__ = HttpRequest

        decoded_jwt = cookies.get_decoded_jwt(mock_request_with_cookie)

        self.assertEqual(expected_decoded_jwt, decoded_jwt)

    @mock.patch('edx_rest_framework_extensions.auth.jwt.cookies.logger')
    def test_get_decoded_jwt_fails_with_broad_except(self, mock_logger):
        user = UserFactory()
        payload = generate_latest_version_payload(user)
        jwt = generate_jwt_token(payload)

        mock_request_with_cookie = mock.Mock(COOKIES={'edx-jwt-cookie': jwt})

        # Fails because the request is a mock, and not a Django HttpRequest
        self.assertIsNone(cookies.get_decoded_jwt(mock_request_with_cookie))

        mock_logger.info.assert_called_once_with(
            "get_decoded_jwt: Unknown error decoding Jwt cookie. AssertionError('The `request` argument must "
            "be an instance of `django.http.HttpRequest`, not `unittest.mock.Mock`.')"
        )

    @override_settings(DISABLE_NEW_JWT_COOKIE_PROCESSING=True)
    def test_get_decoded_jwt_legacy_success_with_mock_request(self):
        """
        Test legacy processing.

        To be removed with DISABLE_NEW_JWT_COOKIE_PROCESSING.
        """
        user = UserFactory()
        payload = generate_latest_version_payload(user)
        jwt = generate_jwt_token(payload)

        expected_decoded_jwt = jwt_decode_handler(jwt)

        mock_request_with_cookie = mock.Mock(COOKIES={'edx-jwt-cookie': jwt})

        decoded_jwt = cookies.get_decoded_jwt(mock_request_with_cookie)

        # Note: This should succeed, where the newer logic would have failed because
        #   the mock is not an HttpRequest. See test_get_decoded_jwt_fails_with_broad_except
        self.assertEqual(expected_decoded_jwt, decoded_jwt)

    def test_get_decoded_jwt_when_no_cookie(self):
        mock_request = mock.Mock(COOKIES={})

        self.assertIsNone(cookies.get_decoded_jwt(mock_request))
