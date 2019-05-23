"""
Unit tests for jwt cookies module.
"""
import ddt
import mock
from django.test import override_settings, TestCase

from edx_rest_framework_extensions.auth.jwt.decoder import jwt_decode_handler
from edx_rest_framework_extensions.auth.jwt.tests.utils import generate_latest_version_payload, generate_jwt_token
from edx_rest_framework_extensions.tests.factories import UserFactory
from .. import cookies


@ddt.ddt
class TestJwtAuthCookies(TestCase):
    @ddt.data(
        (cookies.jwt_cookie_name, 'JWT_AUTH_COOKIE', 'custom-jwt-cookie-name'),
        (cookies.jwt_cookie_header_payload_name, 'JWT_AUTH_COOKIE_HEADER_PAYLOAD', 'custom-jwt-header-payload-name'),
        (cookies.jwt_cookie_signature_name, 'JWT_AUTH_COOKIE_SIGNATURE', 'custom-jwt-signature-name'),
        (cookies.jwt_refresh_cookie_name, 'JWT_AUTH_REFRESH_COOKIE', 'custom-jwt-refresh-name'),
    )
    @ddt.unpack
    def test_get_setting_value(self, jwt_cookie_func, setting_name, setting_value):
        with override_settings(JWT_AUTH={setting_name: setting_value}):
            self.assertEqual(jwt_cookie_func(), setting_value)

    @ddt.data(
        (cookies.jwt_cookie_name, 'edx-jwt-cookie'),
        (cookies.jwt_cookie_header_payload_name, 'edx-jwt-cookie-header-payload'),
        (cookies.jwt_cookie_signature_name, 'edx-jwt-cookie-signature'),
        (cookies.jwt_refresh_cookie_name, 'edx-jwt-refresh-cookie'),
    )
    @ddt.unpack
    def test_get_default_value(self, jwt_cookie_func, expected_default_value):
        self.assertEqual(jwt_cookie_func(), expected_default_value)

    def test_get_decoded_jwt_from_existing_cookie(self):
        user = UserFactory()
        payload = generate_latest_version_payload(user)
        jwt = generate_jwt_token(payload)
        expected_decoded_jwt = jwt_decode_handler(jwt)

        mock_request_with_cookie = mock.Mock(COOKIES={'edx-jwt-cookie': jwt})

        decoded_jwt = cookies.get_decoded_jwt(mock_request_with_cookie)
        self.assertEquals(expected_decoded_jwt, decoded_jwt)

    def test_get_decoded_jwt_when_no_cookie(self):
        mock_request = mock.Mock(COOKIES={})

        self.assertIsNone(cookies.get_decoded_jwt(mock_request))
