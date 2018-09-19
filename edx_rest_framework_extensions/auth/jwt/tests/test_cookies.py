"""
Unit tests for jwt cookies module.
"""
import ddt
from django.test import override_settings, TestCase

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
