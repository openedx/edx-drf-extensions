"""
Unit tests for middlewares.
"""
from itertools import product
import ddt
from mock import patch

from django.test import TestCase, RequestFactory
from rest_framework.authentication import SessionAuthentication
from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication
from rest_framework.decorators import api_view
from rest_framework.views import APIView

from ..middleware import EnsureJWTAuthSettingsMiddleware
from ..permissions import JwtHasScope


class SomeIncludedPermissionClass(object):
    pass


class SomeJwtAuthenticationSubclass(BaseJSONWebTokenAuthentication):
    pass


SOME_INCLUDED_SCOPE = 'some:scope'


def some_auth_decorator(include_jwt_auth, include_required_perm, include_scopes):
    def _decorator(f):
        f.permission_classes = (SomeIncludedPermissionClass,)
        f.authentication_classes = (SessionAuthentication,)
        if include_jwt_auth:
            f.authentication_classes += (SomeJwtAuthenticationSubclass,)
        if include_required_perm:
            f.permission_classes += (JwtHasScope,)
        if include_scopes:
            f.required_scopes = [SOME_INCLUDED_SCOPE]
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
            (True, False),
        )
    )
    @ddt.unpack
    def test_api_views(self, use_function_view, include_jwt_auth, include_required_perm, include_scopes):
        @some_auth_decorator(include_jwt_auth, include_required_perm, include_scopes)
        class SomeClassView(APIView):
            pass

        @api_view(["GET"])
        @some_auth_decorator(include_jwt_auth, include_required_perm, include_scopes)
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

        # Not tested for function API views since the api_view
        # decorator does not copy over the required_scopes field.
        if not use_function_view:
            self._assert_included(
                SOME_INCLUDED_SCOPE,
                getattr(view_class, 'required_scopes', []),
                should_be_included=include_scopes,
            )

        with patch('edx_rest_framework_extensions.middleware.log.warning') as mock_warning:
            self.assertIsNone(
                self.middleware.process_view(self.request, view, None, None)
            )
            self.assertEqual(mock_warning.called, include_jwt_auth and not include_required_perm)

        # verify post-conditions

        # verify permission class updates
        self._assert_included(
            JwtHasScope,
            view_class.permission_classes,
            should_be_included=include_required_perm or include_jwt_auth,
        )

        # verify required_scopes updates
        #  Not supported for function API views since the api_view
        #  decorator does not copy over the required_scopes field.
        if not use_function_view:
            self._assert_included(
                SOME_INCLUDED_SCOPE,
                getattr(view_class, 'required_scopes', []),
                should_be_included=include_scopes,
            )
            self._assert_included(
                EnsureJWTAuthSettingsMiddleware._view_does_not_support_scopes,  # pylint: disable=protected-access
                getattr(view_class, 'required_scopes', []),
                should_be_included=include_jwt_auth and not include_scopes,
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
