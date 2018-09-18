"""
Unit tests for middlewares.
"""
from itertools import product
import ddt
from django.contrib.auth.models import AnonymousUser
from mock import call, patch

from django.test import override_settings, TestCase, RequestFactory
from rest_condition import C
from rest_framework.authentication import SessionAuthentication
from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from edx_rest_framework_extensions.tests.factories import UserFactory
from ..middleware import (
    EnsureJWTAuthSettingsMiddleware,
    RequestMetricsMiddleware,
)
from ..permissions import (
    IsSuperuser,
    IsStaff,
    JwtHasContentOrgFilterForRequestedCourse,
    NotJwtRestrictedApplication,
)


class SomeIncludedPermissionClass(object):
    pass


class SomeJwtAuthenticationSubclass(BaseJSONWebTokenAuthentication):
    pass


def some_auth_decorator(include_jwt_auth, include_required_perm):
    def _decorator(f):
        f.permission_classes = (SomeIncludedPermissionClass,)
        f.authentication_classes = (SessionAuthentication,)
        if include_jwt_auth:
            f.authentication_classes += (SomeJwtAuthenticationSubclass,)
        if include_required_perm:
            f.permission_classes += (NotJwtRestrictedApplication,)
        return f
    return _decorator


@ddt.ddt
class TestEnsureJWTAuthSettingsMiddleware(TestCase):
    def setUp(self):
        super(TestEnsureJWTAuthSettingsMiddleware, self).setUp()
        self.request = RequestFactory().get('/')
        self.middleware = EnsureJWTAuthSettingsMiddleware()

    def _assert_included(self, item, iterator, should_be_included):
        if should_be_included:
            self.assertIn(item, iterator)
        else:
            self.assertNotIn(item, iterator)

    @ddt.data(
        *product(
            ('view_set', 'class_view', 'function_view'),
            (True, False),
            (True, False),
        )
    )
    @ddt.unpack
    def test_api_views(self, view_type, include_jwt_auth, include_required_perm):
        @some_auth_decorator(include_jwt_auth, include_required_perm)
        class SomeClassView(APIView):
            pass

        @some_auth_decorator(include_jwt_auth, include_required_perm)
        class SomeClassViewSet(ViewSet):
            pass

        @api_view(["GET"])
        @some_auth_decorator(include_jwt_auth, include_required_perm)
        def some_function_view(request):
            pass

        views = dict(
            class_view=SomeClassView,
            view_set=SomeClassViewSet.as_view({'get': 'list'}),
            function_view=some_function_view,
        )
        view_classes = dict(
            class_view=SomeClassView,
            view_set=views['view_set'].cls,
            function_view=views['function_view'].view_class,
        )
        view = views[view_type]
        view_class = view_classes[view_type]

        # verify pre-conditions
        self._assert_included(
            SomeJwtAuthenticationSubclass,
            view_class.authentication_classes,
            should_be_included=include_jwt_auth,
        )

        with patch('edx_rest_framework_extensions.middleware.log.warning') as mock_warning:
            self.assertIsNone(
                self.middleware.process_view(self.request, view, None, None)
            )
            self.assertEqual(mock_warning.called, include_jwt_auth and not include_required_perm)

        # verify post-conditions

        # verify permission class updates
        self._assert_included(
            NotJwtRestrictedApplication,
            view_class.permission_classes,
            should_be_included=include_required_perm or include_jwt_auth,
        )

    def test_simple_view(self):
        """
        Verify middleware works for views that don't have an api_view decorator.
        """
        def some_simple_view(request):
            pass

        self.assertIsNone(
            self.middleware.process_view(self.request, some_simple_view, None, None)
        )

    def test_conditional_permissions(self):
        """
        Make sure we handle ConditionalPermissions from rest_condition.
        """
        class HasCondPermView(APIView):
            authentication_classes = (SomeJwtAuthenticationSubclass,)
            original_permission_classes = (
                C(JwtHasContentOrgFilterForRequestedCourse) & NotJwtRestrictedApplication,
                C(IsSuperuser) | IsStaff,
            )
            permission_classes = original_permission_classes

        class HasNoCondPermView(APIView):
            authentication_classes = (SomeJwtAuthenticationSubclass,)
            original_permission_classes = (
                JwtHasContentOrgFilterForRequestedCourse,
                C(IsSuperuser) | IsStaff,
            )
            permission_classes = original_permission_classes

        # NotJwtRestrictedApplication exists (it's nested in a conditional), so the middleware
        # shouldn't modify this class.
        self.middleware.process_view(self.request, HasCondPermView, None, None)

        # Note: ConditionalPermissions don't implement __eq__
        self.assertIs(
            HasCondPermView.original_permission_classes,
            HasCondPermView.permission_classes
        )

        # NotJwtRestrictedApplication does not exist anywhere, so it should be appended
        self.middleware.process_view(self.request, HasNoCondPermView, None, None)

        # Note: ConditionalPermissions don't implement __eq__
        self.assertIsNot(
            HasNoCondPermView.original_permission_classes,
            HasNoCondPermView.permission_classes
        )
        self.assertIn(NotJwtRestrictedApplication, HasNoCondPermView.permission_classes)


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
