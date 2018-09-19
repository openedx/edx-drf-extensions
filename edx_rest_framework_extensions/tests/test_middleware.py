"""
Unit tests for middlewares.
"""
import ddt
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings, TestCase, RequestFactory
from mock import call, patch

from edx_rest_framework_extensions.tests.factories import UserFactory
from edx_rest_framework_extensions.middleware import RequestMetricsMiddleware


@ddt.ddt
class TestRequestMetricsMiddleware(TestCase):
    def setUp(self):
        super(TestRequestMetricsMiddleware, self).setUp()
        self.request = RequestFactory().get('/')
        self.middleware = RequestMetricsMiddleware()

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_no_headers(self, mock_set_custom_metric):
        self.request.user = None
        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_called_once_with('request_auth_type', 'no-user')

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_blank_headers(self, mock_set_custom_metric):
        self.request.META['HTTP_USER_AGENT'] = ''
        self.request.META['HTTP_REFERER'] = ''
        self.request.META['HTTP_AUTHORIZATION'] = ''

        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_called_once_with('request_auth_type', 'no-user')

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_referer_metric(self, mock_set_custom_metric):
        self.request.META['HTTP_REFERER'] = 'test-http-referer'

        self.middleware.process_response(self.request, None)
        expected_calls = [
            call('request_referer', 'test-http-referer'),
            call('request_auth_type', 'no-user'),
        ]
        mock_set_custom_metric.assert_has_calls(expected_calls, any_order=True)

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_rest_client_user_agent_metrics(self, mock_set_custom_metric):
        self.request.META['HTTP_USER_AGENT'] = 'python-requests/2.9.1 edx-rest-api-client/1.7.2 test-client'

        self.middleware.process_response(self.request, None)
        expected_calls = [
            call('request_user_agent', 'python-requests/2.9.1 edx-rest-api-client/1.7.2 test-client'),
            call('request_client_name', 'test-client'),
            call('request_auth_type', 'no-user'),
        ]
        mock_set_custom_metric.assert_has_calls(expected_calls, any_order=True)

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_standard_user_agent_metrics(self, mock_set_custom_metric):
        self.request.META['HTTP_USER_AGENT'] = 'test-user-agent'

        self.middleware.process_response(self.request, None)
        expected_calls = [
            call('request_user_agent', 'test-user-agent'),
            call('request_auth_type', 'no-user'),
        ]
        mock_set_custom_metric.assert_has_calls(expected_calls, any_order=True)

    @ddt.data(
        ('jwt abcdefg', 'jwt'),
        ('bearer abcdefg', 'bearer'),
        ('abcdefg', 'other-token-type'),
    )
    @ddt.unpack
    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_auth_type_token_metric(self, token, expected_token_type, mock_set_custom_metric):
        self.request.META['HTTP_AUTHORIZATION'] = token

        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_called_once_with('request_auth_type', expected_token_type)

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_auth_type_anonymous_metric(self, mock_set_custom_metric):
        self.request.user = AnonymousUser()

        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_called_once_with('request_auth_type', 'unauthenticated')

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_auth_type_session_metric(self, mock_set_custom_metric):
        self.request.user = UserFactory()

        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_called_once_with('request_auth_type', 'session-or-unknown')
