"""
Unit tests for jwt authentication middlewares.
"""
import ddt
from itertools import product
from mock import call, patch

from django.test import TestCase, RequestFactory
from rest_condition import C
from rest_framework.authentication import SessionAuthentication
from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from edx_rest_framework_extensions.permissions import (
    IsStaff,
    IsSuperuser,
    JwtHasContentOrgFilterForRequestedCourse,
    NotJwtRestrictedApplication,
)
from edx_rest_framework_extensions.auth.jwt.cookies import (
    jwt_cookie_name,
    jwt_cookie_header_payload_name,
    jwt_cookie_signature_name,
)
from edx_rest_framework_extensions.auth.jwt.middleware import (
    EnsureJWTAuthSettingsMiddleware,
    JwtAuthCookieMiddleware,
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

        with patch('edx_rest_framework_extensions.auth.jwt.middleware.log.warning') as mock_warning:
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
class TestJwtAuthCookieMiddleware(TestCase):
    def setUp(self):
        super(TestJwtAuthCookieMiddleware, self).setUp()
        self.request = RequestFactory().get('/')
        self.middleware = JwtAuthCookieMiddleware()

    @ddt.data(
        (jwt_cookie_header_payload_name(), jwt_cookie_signature_name()),
        (jwt_cookie_signature_name(), jwt_cookie_header_payload_name()),
    )
    @ddt.unpack
    @patch('edx_rest_framework_extensions.auth.jwt.middleware.log')
    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_missing_cookies(
            self, set_cookie_name, missing_cookie_name, mock_set_custom_metric, mock_log
    ):
        self.request.COOKIES[set_cookie_name] = 'test'
        self.middleware.process_request(self.request)
        self.assertIsNone(self.request.COOKIES.get(jwt_cookie_name()))
        mock_log.warning.assert_called_once_with(
            '%s cookie is missing. JWT auth cookies will not be reconstituted.' %
            missing_cookie_name
        )
        mock_set_custom_metric.assert_called_once_with('request_jwt_cookie', 'missing-{}'.format(missing_cookie_name))

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_no_cookies(self, mock_set_custom_metric):
        self.middleware.process_request(self.request)
        self.assertIsNone(self.request.COOKIES.get(jwt_cookie_name()))
        mock_set_custom_metric.assert_called_once_with('request_jwt_cookie', 'no')

    @patch('edx_django_utils.monitoring.set_custom_metric')
    def test_success(self, mock_set_custom_metric):
        self.request.COOKIES[jwt_cookie_header_payload_name()] = 'header.payload'
        self.request.COOKIES[jwt_cookie_signature_name()] = 'signature'
        self.middleware.process_request(self.request)
        self.assertEqual(self.request.COOKIES[jwt_cookie_name()], 'header.payload.signature')
        mock_set_custom_metric.assert_called_once_with('request_jwt_cookie', 'yes')
