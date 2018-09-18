"""
Unit tests for jwt authentication middlewares.
"""
import ddt
from django.conf import settings
from mock import call, patch

from django.test import override_settings, TestCase, RequestFactory
from ..middleware import (
    JwtAuthCookieMiddleware,
)

DEFAULT_JWT_COOKIE_NAME = 'edx-jwt-cookie'
DEFAULT_JWT_COOKIE_HEADER_PAYLOAD_NAME = 'edx-jwt-cookie-header-payload'
DEFAULT_JWT_COOKIE_SIGNATURE_NAME = 'edx-jwt-cookie-signature'


@ddt.ddt
class TestJwtAuthCookieMiddleware(TestCase):
    def setUp(self):
        super(TestJwtAuthCookieMiddleware, self).setUp()
        self.request = RequestFactory().get('/')
        self.middleware = JwtAuthCookieMiddleware()

    @ddt.data(
        (DEFAULT_JWT_COOKIE_HEADER_PAYLOAD_NAME, DEFAULT_JWT_COOKIE_SIGNATURE_NAME),
        (DEFAULT_JWT_COOKIE_SIGNATURE_NAME, DEFAULT_JWT_COOKIE_HEADER_PAYLOAD_NAME),
    )
    @ddt.unpack
    @patch('edx_rest_framework_extensions.authn.jwt.middleware.log')
    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_missing_cookie_settings_default(
            self, set_cookie_name, missing_cookie_name, mock_set_custom_metric, mock_log
    ):
        self.request.COOKIES[set_cookie_name] = 'test'
        self.middleware.process_request(self.request)
        self.assertIsNone(self.request.COOKIES.get(DEFAULT_JWT_COOKIE_NAME))
        mock_log.warning.assert_called_once_with(
            '%s cookie is missing. JWT auth cookies will not be reconstituted.' %
            missing_cookie_name
        )
        mock_set_custom_metric.assert_called_once_with('request_jwt_cookie', 'missing-{}'.format(missing_cookie_name))

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_jwt_auth_cookie_no_cookies(self, mock_set_custom_metric):
        self.middleware.process_request(self.request)
        self.assertIsNone(self.request.COOKIES.get(DEFAULT_JWT_COOKIE_NAME))
        mock_set_custom_metric.assert_called_once_with('request_jwt_cookie', 'no')

    @override_settings(JWT_AUTH={
        'JWT_AUTH_COOKIE': 'jwt-cookie',
        'JWT_AUTH_COOKIE_HEADER_PAYLOAD': 'header-payload',
        'JWT_AUTH_COOKIE_SIGNATURE': 'signature',
    })
    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_jwt_auth_cookie_settings_success(self, mock_set_custom_metric):
        self.request.COOKIES[settings.JWT_AUTH['JWT_AUTH_COOKIE_HEADER_PAYLOAD']] = 'header.payload'
        self.request.COOKIES[settings.JWT_AUTH['JWT_AUTH_COOKIE_SIGNATURE']] = 'signature'
        self.middleware.process_request(self.request)
        self.assertEqual(self.request.COOKIES[settings.JWT_AUTH['JWT_AUTH_COOKIE']], 'header.payload.signature')
        mock_set_custom_metric.assert_called_once_with('request_jwt_cookie', 'yes')

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_jwt_auth_cookie_defaults_success(self, mock_set_custom_metric):
        self.request.COOKIES[DEFAULT_JWT_COOKIE_HEADER_PAYLOAD_NAME] = 'header.payload'
        self.request.COOKIES[DEFAULT_JWT_COOKIE_SIGNATURE_NAME] = 'signature'
        self.middleware.process_request(self.request)
        self.assertEqual(self.request.COOKIES[DEFAULT_JWT_COOKIE_NAME], 'header.payload.signature')
        mock_set_custom_metric.assert_called_once_with('request_jwt_cookie', 'yes')
