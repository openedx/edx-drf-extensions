""" Tests for permission classes. """

import ddt
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.conf import settings
from time import time
import jwt
import mock

from edx_rest_framework_extensions.tests.factories import UserFactory
from edx_rest_framework_extensions.permissions import IsSuperuser, HasScopedToken
from edx_rest_framework_extensions.tests import factories
from edx_rest_framework_extensions.tests.test_utils import generate_jwt_token

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


def generate_jwt_payload(user):
    """
    Generate a valid JWT payload given a user.
    """
    jwt_issuer_data = settings.JWT_AUTH['JWT_ISSUERS'][0]
    now = int(time())
    ttl = 5
    return {
        'iss': jwt_issuer_data['ISSUER'],
        'aud': jwt_issuer_data['AUDIENCE'],
        'username': user.username,
        'email': user.email,
        'iat': now,
        'filters': ["content_org:edX", "content_org:Microsoft", "user:me"],
        'scopes': ["grades:read"],
        'exp': now + ttl
    }


@ddt.ddt
class HasScopedTokenTests(TestCase):
    """ Tests for HasScopedToken permission class """
    def setUp(self):
        super(HasScopedTokenTests, self).setUp()
        self.user = UserFactory()
        self.payload = generate_jwt_payload(self.user)
        self.jwt = generate_jwt_token(self.payload)
        self.filters = {'content_org': ['edX', 'Microsoft'], 'user': ['me']}

    def test__token_filters(self):
        permission = HasScopedToken()
        self.assertEqual(permission._token_filters(self.payload), self.filters)

    @override_settings(FEATURES={'ENABLE_OAUTH_SCOPE_ENFORCEMENT': False})
    def test_has_permission_true_if_oauth_scope_enforcement_disabled(self):
        request = RequestFactory().get('/')
        request.auth = self.jwt
        permission = HasScopedToken()
        self.assertTrue(permission.has_permission(request, None))

    def test_has_permission_true_for_edx_trusted_application(self):
        request = RequestFactory().get('/')
        self.payload['edx_trusted_application'] = True
        self.jwt = generate_jwt_token(self.payload)
        request.auth = self.jwt
        permission = HasScopedToken()
        self.assertTrue(permission.has_permission(request, None))

    def test_has_permission_false_for_token_version_incompatible(self):
        request = RequestFactory().get('/')
        self.payload['edx_trusted_application'] = False
        self.payload['version'] = 1
        self.jwt = generate_jwt_token(self.payload)
        request.auth = self.jwt
        permission = HasScopedToken()
        self.assertFalse(permission.has_permission(request, None))
