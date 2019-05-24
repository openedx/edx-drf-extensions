# -*- coding: utf-8 -*-
""" Tests for JWT authentication class. """
from logging import Logger

import ddt
import mock
from django.contrib.auth import get_user_model
from django.test import override_settings, RequestFactory, TestCase
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_jwt.authentication import JSONWebTokenAuthentication


from edx_rest_framework_extensions.auth.jwt import authentication
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from edx_rest_framework_extensions.auth.jwt.decoder import jwt_decode_handler
from edx_rest_framework_extensions.auth.jwt.tests.utils import generate_latest_version_payload, generate_jwt_token
from edx_rest_framework_extensions.tests import factories

User = get_user_model()


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

    @ddt.data(True, False)
    def test_get_decoded_jwt_from_auth(self, is_jwt_authentication):
        """ Verify get_decoded_jwt_from_auth returns the appropriate value. """

        # Mock out the `is_jwt_authenticated` method
        authentication.is_jwt_authenticated = lambda request: is_jwt_authentication

        user = factories.UserFactory()
        payload = generate_latest_version_payload(user)
        jwt = generate_jwt_token(payload)
        mock_request_with_cookie = mock.Mock(COOKIES={}, auth=jwt)

        expected_decoded_jwt = jwt_decode_handler(jwt) if is_jwt_authentication else None

        decoded_jwt = authentication.get_decoded_jwt_from_auth(mock_request_with_cookie)
        self.assertEquals(expected_decoded_jwt, decoded_jwt)
