# -*- coding: utf-8 -*-
""" Tests for authentication classes. """
import json
from logging import Logger

import ddt
import httpretty
import mock
from django.contrib.auth import get_user_model
from django.test import override_settings, RequestFactory, TestCase
from requests import RequestException
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from edx_rest_framework_extensions.authentication import BearerAuthentication, JwtAuthentication
from edx_rest_framework_extensions.tests import factories

OAUTH2_ACCESS_TOKEN_URL = 'http://example.com/oauth2/access_token/'
OAUTH2_USER_INFO_URL = 'http://example.com/oauth2/user_info/'
USER_INFO = {
    'username': 'jdoe',
    'first_name': 'Jane',
    'last_name': 'Doê',
    'email': 'jdoe@example.com',
}
User = get_user_model()


class AccessTokenMixin(object):
    """ Test mixin for dealing with OAuth2 access tokens. """
    DEFAULT_TOKEN = 'abc123'

    def mock_user_info_response(self, status=200, username=None):
        """ Mock the user info endpoint response of the OAuth2 provider. """

        username = username or USER_INFO['username']
        data = {
            'family_name': USER_INFO['last_name'],
            'preferred_username': username,
            'given_name': USER_INFO['first_name'],
            'email': USER_INFO['email'],
        }

        httpretty.register_uri(
            httpretty.GET,
            OAUTH2_USER_INFO_URL,
            body=json.dumps(data),
            content_type='application/json',
            status=status
        )


@override_settings(EDX_DRF_EXTENSIONS={'OAUTH2_USER_INFO_URL': OAUTH2_USER_INFO_URL})
class BearerAuthenticationTests(AccessTokenMixin, TestCase):
    """ Tests for the BearerAuthentication class. """
    TOKEN_NAME = 'Bearer'

    def setUp(self):
        super(BearerAuthenticationTests, self).setUp()
        self.auth = BearerAuthentication()
        self.factory = RequestFactory()

    def create_authenticated_request(self, token=AccessTokenMixin.DEFAULT_TOKEN, token_name=TOKEN_NAME):
        """ Returns a Request with the authorization set using the specified values. """
        auth_header = '{token_name} {token}'.format(token_name=token_name, token=token)
        request = self.factory.get('/', HTTP_AUTHORIZATION=auth_header)
        return request

    def assert_user_authenticated(self):
        """ Assert a user can be authenticated with a bearer token. """
        user = factories.UserFactory()
        self.mock_user_info_response(username=user.username)

        request = self.create_authenticated_request()
        self.assertEqual(self.auth.authenticate(request), (user, self.DEFAULT_TOKEN))

    def assert_authentication_failed(self, token=AccessTokenMixin.DEFAULT_TOKEN, token_name=TOKEN_NAME):
        """ Assert authentication fails for a generated request. """
        request = self.create_authenticated_request(token=token, token_name=token_name)
        self.assertRaises(AuthenticationFailed, self.auth.authenticate, request)

    def test_authenticate_header(self):
        """ The method should return the string Bearer. """
        self.assertEqual(self.auth.authenticate_header(self.create_authenticated_request()), 'Bearer')

    @override_settings(EDX_DRF_EXTENSIONS={'OAUTH2_USER_INFO_URL': None})
    def test_authenticate_no_user_info_url(self):
        """ If the setting OAUTH2_USER_INFO_URL is not set, the method returns None. """

        # Empty value
        self.assertIsNone(self.auth.authenticate(self.create_authenticated_request()))

        # Missing value
        with override_settings(EDX_DRF_EXTENSIONS={}):
            self.assertIsNone(self.auth.authenticate(self.create_authenticated_request()))

    def test_authenticate_invalid_token(self):
        """ If no token is supplied, or if the token contains spaces, the method should raise an exception. """

        # Missing token
        self.assert_authentication_failed(token='')

        # Token with spaces
        self.assert_authentication_failed(token='abc 123 456')

    def test_authenticate_invalid_token_name(self):
        """ If the token name is not Bearer, the method should return None. """
        request = self.create_authenticated_request(token_name='foobar')
        self.assertIsNone(self.auth.authenticate(request))

    @httpretty.activate
    def test_authenticate_inactive_user(self):
        """ If the user matching the access token is inactive, the method should raise an exception. """
        user = factories.UserFactory(is_active=False)
        self.mock_user_info_response(username=user.username)
        self.assert_authentication_failed()

    @httpretty.activate
    def test_authenticate_invalid_token_response(self):
        """ If the user info endpoint does not return HTTP 200, the method should return raise an exception. """
        self.mock_user_info_response(status=400)
        self.assert_authentication_failed()

    @httpretty.activate
    def test_authenticate(self):
        """ If the access token is valid, the user exists, and is active, a tuple containing
        the user and token should be returned.
        """
        self.assert_user_authenticated()

    @httpretty.activate
    def test_authenticate_as_new_user(self):
        """ Verify a new user is created. """
        self.mock_user_info_response()
        request = self.create_authenticated_request()
        actual_user, actual_token = self.auth.authenticate(request)

        self.assertEqual(actual_token, self.DEFAULT_TOKEN)
        self.assertEqual(actual_user, User.objects.get(username=USER_INFO['username']))

    @httpretty.activate
    def test_authenticate_user_creation_with_existing_user(self):
        """ Verify an existing user is returned, if the user already exists. """
        user = factories.UserFactory(username=USER_INFO['username'])
        self.mock_user_info_response()
        request = self.create_authenticated_request()
        actual_user, actual_token = self.auth.authenticate(request)

        self.assertEqual(actual_token, self.DEFAULT_TOKEN)
        self.assertEqual(actual_user, user)

    @httpretty.activate
    def test_authenticate_user_creation_with_request_status_failure(self):
        """ Verify authentication fails if the request to retrieve user info returns a non-200 status. """
        original_user_count = User.objects.all().count()
        self.mock_user_info_response(status=401)
        request = self.create_authenticated_request()

        self.assertRaises(AuthenticationFailed, self.auth.authenticate, request)
        self.assertEqual(User.objects.all().count(), original_user_count)

    def test_authenticate_user_creation_with_request_exception(self):
        """ Verify authentication fails if the request to retrieve user info raises an exception. """
        original_user_count = User.objects.all().count()
        request = self.create_authenticated_request()

        with mock.patch('requests.get', mock.Mock(side_effect=RequestException)):
            self.assertRaises(AuthenticationFailed, self.auth.authenticate, request)

        self.assertEqual(User.objects.all().count(), original_user_count)


@ddt.ddt
class JwtAuthenticationTests(TestCase):
    """ JWT Authentication class tests. """

    def get_jwt_payload(self, **additional_claims):
        """ Returns a JWT payload with the necessary claims to create a new user. """
        email = 'gcostanza@gmail.com'
        username = 'gcostanza'
        payload = dict({'preferred_username': username, 'email': email}, **additional_claims)

        return payload

    @ddt.data(True, False)
    def test_authenticate_credentials_user_creation(self, is_staff):
        """ Test whether the user model is being created and assigned fields from the payload. """

        payload = self.get_jwt_payload(administrator=is_staff)
        user = JwtAuthentication().authenticate_credentials(payload)
        self.assertEqual(user.username, payload['preferred_username'])
        self.assertEqual(user.email, payload['email'])
        self.assertEqual(user.is_staff, is_staff)

    def test_authenticate_credentials_user_updates_default_attributes(self):
        """ Test whether the user model is being assigned default fields from the payload. """

        username = 'gcostanza'
        old_email = 'tbone@gmail.com'
        new_email = 'koko@gmail.com'

        user = factories.UserFactory(email=old_email, username=username, is_staff=False)
        self.assertEqual(user.email, old_email)
        self.assertFalse(user.is_staff)

        payload = {'username': username, 'email': new_email, 'is_staff': True}

        user = JwtAuthentication().authenticate_credentials(payload)
        self.assertEqual(user.email, new_email)
        self.assertFalse(user.is_staff)

    @override_settings(
        EDX_DRF_EXTENSIONS={'JWT_PAYLOAD_USER_ATTRIBUTE_MAPPING': {'email': 'email', 'is_staff': 'is_staff'}}
    )
    def test_authenticate_credentials_user_attributes_custom_attributes(self):
        """ Test whether the user model is being assigned all custom fields from the payload. """

        username = 'ckramer'
        old_email = 'ckramer@hotmail.com'
        new_email = 'cosmo@hotmail.com'

        user = factories.UserFactory(email=old_email, username=username, is_staff=False)
        self.assertEqual(user.email, old_email)
        self.assertFalse(user.is_staff)

        payload = {'username': username, 'email': new_email, 'is_staff': True}

        user = JwtAuthentication().authenticate_credentials(payload)
        self.assertEqual(user.email, new_email)
        self.assertTrue(user.is_staff)

    def test_authenticate_credentials_user_retrieval_failed(self):
        """ Verify exceptions raised during user retrieval are properly logged. """

        with mock.patch.object(User.objects, 'get_or_create', side_effect=ValueError):
            with mock.patch.object(Logger, 'exception') as logger:
                self.assertRaises(
                    AuthenticationFailed,
                    JwtAuthentication().authenticate_credentials,
                    {'username': 'test', 'email': 'test@example.com'}
                )
                logger.assert_called_with('User retrieval failed.')

    def test_authenticate_credentials_no_usernames(self):
        """ Verify an AuthenticationFailed exception is raised if the payload contains no username claim. """
        with self.assertRaises(AuthenticationFailed):
            JwtAuthentication().authenticate_credentials({'email': 'test@example.com'})

    def test_authenticate(self):
        """ Verify exceptions raised during authentication are properly logged. """
        request = RequestFactory().get('/')

        with mock.patch.object(JSONWebTokenAuthentication, 'authenticate', side_effect=Exception):
            with mock.patch.object(Logger, 'debug') as logger:
                self.assertRaises(
                    Exception,
                    JwtAuthentication().authenticate,
                    request
                )
                self.assertTrue(logger.called)
