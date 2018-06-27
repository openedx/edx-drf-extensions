"""
Unit tests for middlewares.
"""
from itertools import product
import ddt
from mock import patch

from django.test import TestCase, RequestFactory
from rest_condition import C
from rest_framework.authentication import SessionAuthentication
from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication
from rest_framework.decorators import api_view
from rest_framework.views import APIView

from ..middleware import EnsureJWTAuthSettingsMiddleware
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
            (True, False),
            (True, False),
            (True, False),
        )
    )
    @ddt.unpack
    def test_api_views(self, use_function_view, include_jwt_auth, include_required_perm):
        @some_auth_decorator(include_jwt_auth, include_required_perm)
        class SomeClassView(APIView):
            pass

        @api_view(["GET"])
        @some_auth_decorator(include_jwt_auth, include_required_perm)
        def some_function_view(request):
            pass

        view = some_function_view if use_function_view else SomeClassView
        view_class = view.view_class if use_function_view else view

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
