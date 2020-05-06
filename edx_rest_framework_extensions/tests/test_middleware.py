"""
Unit tests for middlewares.
"""
import ddt
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from edx_django_utils.cache import RequestCache
from mock import call, patch

from edx_rest_framework_extensions.auth.jwt.constants import USE_JWT_COOKIE_HEADER
from edx_rest_framework_extensions.auth.jwt.cookies import jwt_cookie_name
from edx_rest_framework_extensions.middleware import RequestMetricsMiddleware
from edx_rest_framework_extensions.tests.factories import UserFactory


@ddt.ddt
class TestRequestMetricsMiddleware(TestCase):
    def setUp(self):
        super(TestRequestMetricsMiddleware, self).setUp()
        RequestCache.clear_all_namespaces()
        self.request = RequestFactory().get('/')
        self.middleware = RequestMetricsMiddleware()

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_auth_type_guess_anonymous_metric(self, mock_set_custom_metric):
        self.request.user = AnonymousUser()

        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_called_once_with('request_auth_type_guess', 'unauthenticated')

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_no_headers(self, mock_set_custom_metric):
        self.request.user = None
        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_called_once_with('request_auth_type_guess', 'no-user')

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_blank_headers(self, mock_set_custom_metric):
        self.request.META['HTTP_USER_AGENT'] = ''
        self.request.META['HTTP_REFERER'] = ''
        self.request.META['HTTP_AUTHORIZATION'] = ''

        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_called_once_with('request_auth_type_guess', 'no-user')

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_referer_metric(self, mock_set_custom_metric):
        self.request.META['HTTP_REFERER'] = 'test-http-referer'

        self.middleware.process_response(self.request, None)
        expected_calls = [
            call('request_referer', 'test-http-referer'),
            call('request_auth_type_guess', 'no-user'),
        ]
        mock_set_custom_metric.assert_has_calls(expected_calls, any_order=True)

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_rest_client_user_agent_metrics(self, mock_set_custom_metric):
        self.request.META['HTTP_USER_AGENT'] = 'python-requests/2.9.1 edx-rest-api-client/1.7.2 test-client'

        self.middleware.process_response(self.request, None)
        expected_calls = [
            call('request_user_agent', 'python-requests/2.9.1 edx-rest-api-client/1.7.2 test-client'),
            call('request_client_name', 'test-client'),
            call('request_auth_type_guess', 'no-user'),
        ]
        mock_set_custom_metric.assert_has_calls(expected_calls, any_order=True)

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_standard_user_agent_metrics(self, mock_set_custom_metric):
        self.request.META['HTTP_USER_AGENT'] = 'test-user-agent'

        self.middleware.process_response(self.request, None)
        expected_calls = [
            call('request_user_agent', 'test-user-agent'),
            call('request_auth_type_guess', 'no-user'),
        ]
        mock_set_custom_metric.assert_has_calls(expected_calls, any_order=True)

    @ddt.data(
        ('jwt abcdefg', 'jwt'),
        ('bearer abcdefg', 'bearer'),
        ('abcdefg', 'other-token-type'),
    )
    @ddt.unpack
    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_auth_type_guess_token_metric(self, token, expected_token_type, mock_set_custom_metric):
        self.request.user = UserFactory()
        self.request.META['HTTP_AUTHORIZATION'] = token

        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_any_call('request_auth_type_guess', expected_token_type)

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_auth_type_guess_jwt_cookie_metric(self, mock_set_custom_metric):
        self.request.user = UserFactory()
        self.request.META[USE_JWT_COOKIE_HEADER] = True
        self.request.COOKIES[jwt_cookie_name()] = 'reconstituted-jwt-cookie'

        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_any_call('request_auth_type_guess', 'jwt-cookie')

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_auth_type_guess_session_metric(self, mock_set_custom_metric):
        self.request.user = UserFactory()

        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_any_call('request_auth_type_guess', 'session-or-other')

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_user_id_metric(self, mock_set_custom_metric):
        self.request.user = UserFactory()

        self.middleware.process_response(self.request, None)
        mock_set_custom_metric.assert_any_call('request_user_id', self.request.user.id)
        mock_set_custom_metric.assert_any_call(
            'request_authenticated_user_found_in_middleware', 'process_response'
        )

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_request_user_id_metric_with_exception(self, mock_set_custom_metric):
        self.request.user = UserFactory()

        self.middleware.process_exception(self.request, None)
        mock_set_custom_metric.assert_any_call('request_user_id', self.request.user.id)
        mock_set_custom_metric.assert_any_call(
            'request_authenticated_user_found_in_middleware', 'process_exception'
        )

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_authenticated_user_found_in_process_request(self, mock_set_custom_metric):
        self.request.user = UserFactory()
        self.middleware.process_request(self.request)
        self.middleware.process_response(self.request, None)

        mock_set_custom_metric.assert_any_call(
            'request_authenticated_user_found_in_middleware', 'process_request'
        )

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_authenticated_user_found_in_process_view(self, mock_set_custom_metric):
        self.request.user = UserFactory()
        self.middleware.process_view(self.request, None, None, None)
        self.middleware.process_response(self.request, None)

        mock_set_custom_metric.assert_any_call(
            'request_authenticated_user_found_in_middleware', 'process_view'
        )

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_authenticated_user_found_is_properly_reset(self, mock_set_custom_metric):
        # set user before process_request
        self.request.user = UserFactory()
        self.middleware.process_request(self.request)
        self.middleware.process_response(self.request, None)

        mock_set_custom_metric.assert_any_call(
            'request_authenticated_user_found_in_middleware', 'process_request'
        )

        # set up new request and set user before process_response
        mock_set_custom_metric.reset_mock()
        RequestCache.clear_all_namespaces()
        self.request = RequestFactory().get('/')
        self.request.user = UserFactory()
        self.middleware.process_response(self.request, None)

        mock_set_custom_metric.assert_any_call(
            'request_authenticated_user_found_in_middleware', 'process_response'
        )
