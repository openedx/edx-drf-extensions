""" Tests for permission classes. """

import ddt
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, TestCase
from mock import Mock, patch
from rest_framework.views import APIView

from edx_rest_framework_extensions.tests.factories import UserFactory
from edx_rest_framework_extensions.authentication import JwtAuthentication
from edx_rest_framework_extensions.permissions import (
    IsSuperuser,
    JwtHasContentOrgFilterForRequestedCourse,
    JwtHasScope,
)
from edx_rest_framework_extensions.tests import factories
from edx_rest_framework_extensions.tests.test_utils import generate_jwt


@ddt.ddt
class IsSuperuserTests(TestCase):
    """ Tests for the IsSuperuser permission class. """

    @ddt.data(True, False)
    def test_has_permission(self, has_permission):
        """ Verify the method only returns True if the user is a superuser. """
        request = RequestFactory().get('/')
        request.user = factories.UserFactory(is_superuser=has_permission)
        permission = IsSuperuser()
        self.assertEqual(permission.has_permission(request, None), has_permission)

    @ddt.data(None, AnonymousUser())
    def test_has_permission_with_invalid_users(self, user):
        """ Verify the method returns False if the request's user is not a real user. """
        request = RequestFactory().get('/')
        request.user = user
        permission = IsSuperuser()
        self.assertFalse(permission.has_permission(request, None))


@ddt.ddt
class JwtHasScopeTests(TestCase):
    """ Tests for JwtHasScope permission class. """
    def setUp(self):
        super(JwtHasScopeTests, self).setUp()
        self.user = UserFactory()

    @ddt.data(
        (True, JwtAuthentication(), ('test:read',), ('test:read',), True),
        (True, JwtAuthentication(), ('test:write'), ('test:read',), False),
        (True, JwtAuthentication(), (), ('test:read',), False),
        (True, None, (), ('test:read'), True),
        (False, JwtAuthentication(), (), ('test:read'), True),
        (False, None, (), ('test:read'), True),
    )
    @ddt.unpack
    @patch('edx_rest_framework_extensions.decorators.waffle.switch_is_active')
    def test_has_permission(self, enforce_scopes, authentication_class, jwt_scopes,
                            required_scopes, expected_result, waffle_mock):
        """
        Test that the permission check returns the expected result when scopes are validated.
        """
        waffle_mock.return_value = enforce_scopes
        request = RequestFactory().get('/')
        request.successful_authenticator = authentication_class
        request.auth = generate_jwt(self.user, scopes=jwt_scopes)
        view = Mock(required_scopes=required_scopes)
        self.assertEqual(JwtHasScope().has_permission(request, view), expected_result)

    @patch('edx_rest_framework_extensions.decorators.waffle.switch_is_active')
    def test_has_permission_missing_required_scopes(self, waffle_mock):
        """
        Test that the permission check raises an exception if
        required_scopes was not defined on the view.
        """
        waffle_mock.return_value = True
        request = RequestFactory().get('/')
        request.successful_authenticator = JwtAuthentication()
        request.auth = generate_jwt(self.user, scopes=['test:read'])
        view = APIView()
        with self.assertRaises(ImproperlyConfigured):
            JwtHasScope().has_permission(request, view)


@ddt.ddt
class JwtHasContentOrgFilterForRequestedCourseTests(TestCase):
    """ Tests for JwtHasContentOrgFilterForRequestedCourse permission class. """
    def setUp(self):
        super(JwtHasContentOrgFilterForRequestedCourseTests, self).setUp()
        self.user = UserFactory()

    @ddt.data(
        (True, JwtAuthentication(), ['content_org:edX'], {'course_id': 'course-v1:edX+DemoX+Demo_Course'}, True),
        (True, JwtAuthentication(), ['content_org:TestX'], {'course_id': 'course-v1:edX+DemoX+Demo_Course'}, False),
        (True, JwtAuthentication(), ['test:TestX'], {'course_id': 'course-v1:edX+DemoX+Demo_Course'}, False),
        (True, JwtAuthentication(), [], {'course_id': 'course-v1:edX+DemoX+Demo_Course'}, False),
        (True, None, [], {'course_id': 'course-v1:edX+DemoX+Demo_Course'}, True),
        (False, JwtAuthentication(), [], {'course_id': 'course-v1:edX+DemoX+Demo_Course'}, True),
        (False, None, [], {'course_id': 'course-v1:edX+DemoX+Demo_Course'}, True),
    )
    @ddt.unpack
    @patch('edx_rest_framework_extensions.decorators.waffle.switch_is_active')
    def test_has_permission(self, enforce_scopes, authentication_class, jwt_filters,
                            view_kwargs, expected_result, waffle_mock):
        """
        Test that the permission check returns the expected result when scopes are validated.
        """
        waffle_mock.return_value = enforce_scopes
        request = RequestFactory().get('/')
        request.successful_authenticator = authentication_class
        request.auth = generate_jwt(self.user, filters=jwt_filters)
        view = Mock(kwargs=view_kwargs)
        self.assertEqual(JwtHasContentOrgFilterForRequestedCourse().has_permission(request, view), expected_result)
