""" Tests for JWT authentication class. """
from logging import Logger
from unittest import mock

import ddt
from django.contrib.auth import get_user_model
from django.http.cookie import SimpleCookie
from django.test import RequestFactory, TestCase, override_settings
from django.urls import re_path as url_pattern
from django.urls import reverse
from jwt import exceptions as jwt_exceptions
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from edx_rest_framework_extensions.auth.jwt import authentication
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from edx_rest_framework_extensions.auth.jwt.constants import USE_JWT_COOKIE_HEADER
from edx_rest_framework_extensions.auth.jwt.cookies import jwt_cookie_name
from edx_rest_framework_extensions.auth.jwt.decoder import jwt_decode_handler
from edx_rest_framework_extensions.auth.jwt.tests.utils import (
    generate_jwt_token,
    generate_latest_version_payload,
)
from edx_rest_framework_extensions.config import (
    ENABLE_FORGIVING_JWT_COOKIES,
    ENABLE_JWT_VS_SESSION_USER_CHECK,
)
from edx_rest_framework_extensions.settings import get_setting
from edx_rest_framework_extensions.tests import factories


User = get_user_model()


class IsAuthenticatedView(APIView):
    authentication_classes = (JwtAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):  # pylint: disable=unused-argument
        return Response({'success': True})


urlpatterns = [
    url_pattern(
        r'^isauthenticated/$',
        IsAuthenticatedView.as_view(),
        name='authenticated-view',
    ),
]


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

    @override_settings(
        EDX_DRF_EXTENSIONS={
            'JWT_PAYLOAD_USER_ATTRIBUTE_MAPPING': {
                'email': 'email',
                'is_staff': 'is_staff',
                'tags': 'tags',
                'fun_attr': 'fun_attr',
                'fruit': 'fruit'
            },
            'JWT_PAYLOAD_MERGEABLE_USER_ATTRIBUTES': [
                'tags',
                'fun_attr',
                'fruit'
            ]
        }
    )
    def test_authenticate_credentials_user_attributes_merge_attributes(self):
        """ Test whether the user model is being assigned all custom fields from the payload. """

        username = 'ckramer'
        email = 'ckramer@hotmail.com'
        old_tags = {'country': 'USA', 'browser': 'Firefox'}
        new_tags = {'browser': 'Chrome', 'new_attr': 'here!'}
        new_fun_attr = {'shiny': 'object'}
        expected_tags = {'country': 'USA', 'browser': 'Chrome', 'new_attr': 'here!'}
        old_fruit = {'fruit': 'apple'}

        user = factories.UserFactory(email=email, username=username, is_staff=False)
        setattr(user, 'tags', old_tags)
        setattr(user, 'fruit', old_fruit)
        self.assertEqual(user.email, email)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.tags, old_tags)
        self.assertEqual(user.fruit, old_fruit)  # pylint: disable=no-member

        payload = {'username': username, 'email': email, 'is_staff': True, 'tags': new_tags, 'fun_attr': new_fun_attr}

        # Patch get_or_create so that our tags attribute is on the user object
        with mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.get_user_model') as mock_get_user_model:
            mock_get_user_model().objects.get_or_create.return_value = (user, False)

            user = JwtAuthentication().authenticate_credentials(payload)
        self.assertEqual(user.tags, expected_tags)
        self.assertEqual(user.email, email)
        self.assertTrue(user.is_staff)
        self.assertEqual(user.fun_attr, new_fun_attr)
        self.assertEqual(user.fruit, old_fruit)

    @override_settings(
        EDX_DRF_EXTENSIONS={
            'JWT_PAYLOAD_USER_ATTRIBUTE_MAPPING': {'email': 'email', 'is_staff': 'is_staff', 'tags': 'tags'},
            'JWT_PAYLOAD_MERGEABLE_USER_ATTRIBUTES': ['tags']
        }
    )
    def test_authenticate_credentials_user_attributes_new_mergeable_attributes(self):
        """ Test whether the user model is being assigned all custom fields from the payload. """

        username = 'ckramer'
        email = 'ckramer@hotmail.com'
        new_tags = {'browser': 'Chrome'}

        user = factories.UserFactory(email=email, username=username, is_staff=False)
        self.assertEqual(user.email, email)
        self.assertFalse(user.is_staff)

        payload = {'username': username, 'email': email, 'is_staff': True, 'tags': new_tags}

        # Patch get_or_create so that our tags attribute is on the user object
        with mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.get_user_model') as mock_get_user_model:
            mock_get_user_model().objects.get_or_create.return_value = (user, False)

            user = JwtAuthentication().authenticate_credentials(payload)
        self.assertEqual(user.tags, new_tags)
        self.assertEqual(user.email, email)
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
                logger.assert_called_with('[edx-drf-extensions] User retrieval failed for username test.')

    def test_authenticate_credentials_no_usernames(self):
        """ Verify an AuthenticationFailed exception is raised if the payload contains no username claim. """
        with self.assertRaises(AuthenticationFailed):
            JwtAuthentication().authenticate_credentials({'email': 'test@example.com'})

    @mock.patch.object(JwtAuthentication, 'enforce_csrf')
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_with_correct_jwt_cookie(self, mock_set_custom_attribute, mock_enforce_csrf):
        """ Verify authenticate succeeds with a valid JWT cookie. """
        request = RequestFactory().post('/')

        request.META[USE_JWT_COOKIE_HEADER] = 'true'

        request.COOKIES[jwt_cookie_name()] = self._get_test_jwt_token()

        assert JwtAuthentication().authenticate(request)
        mock_enforce_csrf.assert_called_with(request)
        mock_set_custom_attribute.assert_any_call(
            'is_forgiving_jwt_cookies_enabled',
            get_setting(ENABLE_FORGIVING_JWT_COOKIES)
        )
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'success-cookie')

    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_csrf_protected(self, mock_set_custom_attribute):
        """
        Ensure authenticate for JWTs properly handles CSRF errors.

        Note: When using forgiving JWTs, all JWT cookie exceptions, including CSRF, will
        result in a None so that other authentication classes will also be checked.
        """
        request = RequestFactory().post('/')

        request.META[USE_JWT_COOKIE_HEADER] = 'true'
        # Set a sample JWT cookie. We mock the auth response but we still want
        # to ensure that there is jwt set because there is other logic that
        # checks for the jwt to be set before moving forward with CSRF checks.
        request.COOKIES[jwt_cookie_name()] = 'foo'

        with mock.patch.object(JSONWebTokenAuthentication, 'authenticate', return_value=('mock-user', "mock-auth")):
            if get_setting(ENABLE_FORGIVING_JWT_COOKIES):
                assert JwtAuthentication().authenticate(request) is None
                mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'forgiven-failure')
            else:
                with self.assertRaises(PermissionDenied) as context_manager:
                    JwtAuthentication().authenticate(request)
                assert context_manager.exception.detail.startswith('CSRF Failed')
                mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'failed-cookie')

        mock_set_custom_attribute.assert_any_call(
            'jwt_auth_failed',
            "Exception:PermissionDenied('CSRF Failed: CSRF cookie not set.')",
        )

    @ddt.data(True, False)
    def test_get_decoded_jwt_from_auth(self, is_jwt_authentication):
        """ Verify get_decoded_jwt_from_auth returns the appropriate value. """

        # Mock out the `is_jwt_authenticated` method
        authentication.is_jwt_authenticated = lambda request: is_jwt_authentication

        jwt_token = self._get_test_jwt_token()
        mock_request_with_cookie = mock.Mock(COOKIES={}, auth=jwt_token)

        expected_decoded_jwt = jwt_decode_handler(jwt_token) if is_jwt_authentication else None

        decoded_jwt = authentication.get_decoded_jwt_from_auth(mock_request_with_cookie)
        self.assertEqual(expected_decoded_jwt, decoded_jwt)

    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_with_correct_jwt_authorization(self, mock_set_custom_attribute):
        """
        With JWT header it continues and validates the credentials.

        Note: CSRF protection should be skipped for this case, with no PermissionDenied.
        """
        jwt_token = self._get_test_jwt_token()
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f"JWT {jwt_token}")
        assert JwtAuthentication().authenticate(request)
        mock_set_custom_attribute.assert_any_call(
            'is_forgiving_jwt_cookies_enabled',
            get_setting(ENABLE_FORGIVING_JWT_COOKIES)
        )
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'success-auth-header')

    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_with_incorrect_jwt_authorization(self, mock_set_custom_attribute):
        """ With JWT header it continues and validates the credentials and throws error. """
        auth_header = '{token_name} {token}'.format(token_name='JWT', token='wrongvalue')
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=auth_header)
        with self.assertRaises(AuthenticationFailed):
            JwtAuthentication().authenticate(request)
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'failed-auth-header')

    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_with_correct_jwt_authorization_and_bad_cookie(self, mock_set_custom_attribute):
        """
        With JWT header it continues and validates the credentials and ignores the invalid cookie.

        Note: CSRF protection should be skipped for this case, with no PermissionDenied.
        """
        jwt_token = self._get_test_jwt_token()
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=f"JWT {jwt_token}")
        request.COOKIES[jwt_cookie_name()] = 'foo'
        assert JwtAuthentication().authenticate(request)
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'success-auth-header')

    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_with_bearer_token(self, mock_set_custom_attribute):
        """ Returns a None for bearer header request. """
        auth_header = '{token_name} {token}'.format(token_name='Bearer', token='abc123')
        request = RequestFactory().get('/', HTTP_AUTHORIZATION=auth_header)
        self.assertIsNone(JwtAuthentication().authenticate(request))
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'n/a')

    @override_settings(
        EDX_DRF_EXTENSIONS={ENABLE_JWT_VS_SESSION_USER_CHECK: True},
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_jwt_and_session_mismatch(self, mock_set_custom_attribute):
        """ Tests monitoring for JWT cookie when there is a session user mismatch """
        session_user_id = 111
        session_user = factories.UserFactory(id=session_user_id)
        jwt_user = factories.UserFactory(id=222)
        self.client.cookies = SimpleCookie({
            jwt_cookie_name(): self._get_test_jwt_token(user=jwt_user),
        })

        self.client.force_login(session_user)
        response = self.client.get(reverse('authenticated-view'))

        mock_set_custom_attribute.assert_any_call('is_jwt_vs_session_user_check_enabled', True)
        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_session_user_id', session_user_id)
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'success-cookie')
        assert response.status_code == 200

    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_jwt_and_session_mismatch_bad_signature_cookie(self, mock_set_custom_attribute):
        """ Tests monitoring for JWT cookie with a bad signature when there is a session user mismatch """
        session_user_id = 111
        session_user = factories.UserFactory(id=session_user_id)
        jwt_user_id = 222
        jwt_user = factories.UserFactory(id=jwt_user_id)
        self.client.cookies = SimpleCookie({
            jwt_cookie_name(): self._get_test_jwt_token(user=jwt_user, is_valid_signature=False),
        })

        enable_forgiving_jwt_cookies = get_setting(ENABLE_FORGIVING_JWT_COOKIES)
        with override_settings(
            EDX_DRF_EXTENSIONS={
                ENABLE_FORGIVING_JWT_COOKIES: enable_forgiving_jwt_cookies,
                ENABLE_JWT_VS_SESSION_USER_CHECK: True,
            },
            MIDDLEWARE=(
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
            ),
            ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
        ):
            self.client.force_login(session_user)
            response = self.client.get(reverse('authenticated-view'))

        mock_set_custom_attribute.assert_any_call('is_jwt_vs_session_user_check_enabled', True)
        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_session_user_id', session_user_id)
        mock_set_custom_attribute.assert_any_call('failed_jwt_cookie_user_id', jwt_user_id)
        if enable_forgiving_jwt_cookies:
            mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'user-mismatch-failure')
        else:
            mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'failed-cookie')
        assert response.status_code == 401

    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_jwt_and_session_mismatch_invalid_cookie(self, mock_set_custom_attribute):
        """ Tests monitoring for invalid JWT cookie when there is a session user mismatch """
        session_user_id = 111
        session_user = factories.UserFactory(id=session_user_id)
        self.client.cookies = SimpleCookie({
            jwt_cookie_name(): 'invalid-cookie',
        })

        enable_forgiving_jwt_cookies = get_setting(ENABLE_FORGIVING_JWT_COOKIES)
        with override_settings(
            EDX_DRF_EXTENSIONS={
                ENABLE_FORGIVING_JWT_COOKIES: enable_forgiving_jwt_cookies,
                ENABLE_JWT_VS_SESSION_USER_CHECK: True,
            },
            MIDDLEWARE=(
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
            ),
            ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
        ):
            self.client.force_login(session_user)
            response = self.client.get(reverse('authenticated-view'))

        mock_set_custom_attribute.assert_any_call('is_jwt_vs_session_user_check_enabled', True)
        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_session_user_id', session_user_id)
        mock_set_custom_attribute.assert_any_call('failed_jwt_cookie_user_id', 'decode-error')
        if enable_forgiving_jwt_cookies:
            mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'user-mismatch-failure')
        else:
            mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'failed-cookie')
        assert response.status_code == 401

    @override_settings(
        EDX_DRF_EXTENSIONS={ENABLE_JWT_VS_SESSION_USER_CHECK: True},
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_jwt_and_session_match(self, mock_set_custom_attribute):
        """ Tests monitoring for JWT cookie when session user matches """
        test_user = factories.UserFactory()
        self.client.cookies = SimpleCookie({
            jwt_cookie_name(): self._get_test_jwt_token(user=test_user),
        })

        self.client.force_login(test_user)
        response = self.client.get(reverse('authenticated-view'))

        mock_set_custom_attribute.assert_any_call('is_jwt_vs_session_user_check_enabled', True)
        set_custom_attribute_keys = [call.args[0] for call in mock_set_custom_attribute.call_args_list]
        assert 'is_jwt_vs_session_user_check_enabled' in set_custom_attribute_keys
        assert 'jwt_auth_mismatch_session_user_id' not in set_custom_attribute_keys
        assert response.status_code == 200

    @override_settings(
        EDX_DRF_EXTENSIONS={ENABLE_JWT_VS_SESSION_USER_CHECK: True},
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_jwt_and_no_session(self, mock_set_custom_attribute):
        """ Tests monitoring for JWT cookie when there is no session """
        test_user = factories.UserFactory()
        self.client.cookies = SimpleCookie({
            jwt_cookie_name(): self._get_test_jwt_token(user=test_user),
        })

        # unlike other tests, there is no force_login call to start the session
        response = self.client.get(reverse('authenticated-view'))

        mock_set_custom_attribute.assert_any_call('is_jwt_vs_session_user_check_enabled', True)
        set_custom_attribute_keys = [call.args[0] for call in mock_set_custom_attribute.call_args_list]
        assert 'is_jwt_vs_session_user_check_enabled' in set_custom_attribute_keys
        assert 'jwt_auth_mismatch_session_user_id' not in set_custom_attribute_keys
        assert response.status_code == 200

    @override_settings(
        EDX_DRF_EXTENSIONS={ENABLE_JWT_VS_SESSION_USER_CHECK: False},
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_jwt_and_session_mismatch_disabled(self, mock_set_custom_attribute):
        """ Tests monitoring disabled for JWT cookie and session user mismatch """
        session_user = factories.UserFactory(id=111)
        jwt_user = factories.UserFactory(id=222)
        self.client.cookies = SimpleCookie({
            jwt_cookie_name(): self._get_test_jwt_token(user=jwt_user),
        })

        self.client.force_login(session_user)
        response = self.client.get(reverse('authenticated-view'))

        mock_set_custom_attribute.assert_any_call('is_jwt_vs_session_user_check_enabled', False)
        set_custom_attribute_keys = [call.args[0] for call in mock_set_custom_attribute.call_args_list]
        assert 'is_jwt_vs_session_user_check_enabled' in set_custom_attribute_keys
        assert 'jwt_auth_mismatch_session_user_id' not in set_custom_attribute_keys
        assert response.status_code == 200

    def _get_test_jwt_token(self, user=None, is_valid_signature=True):
        """ Returns a user and jwt token """
        test_user = factories.UserFactory() if user is None else user
        payload = generate_latest_version_payload(test_user)
        if is_valid_signature:
            jwt_token = generate_jwt_token(payload)
        else:
            jwt_token = generate_jwt_token(payload, signing_key='invalid-key')
        return jwt_token


# We want to duplicate these tests for now while we have two major code paths.  It will get unified once we have a
# single way of doing JWT authentication again.
@override_settings(EDX_DRF_EXTENSIONS={ENABLE_FORGIVING_JWT_COOKIES: True})
class ForgivingJwtAuthenticationTests(JwtAuthenticationTests):  # pylint: disable=test-inherits-tests
    pass


class TestLowestJWTException:
    """
    Test that we're getting the correct exception out of a stack of exceptions when checking a JWT for auth Fails.

    The exception closest to us does not have sufficient useful information so we have to see what other exceptions the
    current exception came from.
    """
    # pylint: disable=broad-exception-caught, raise-missing-from, unused-variable, protected-access

    def test_jwt_exception_in_the_middle(self):
        mock_jwt_exception = jwt_exceptions.DecodeError("Not enough segments")
        try:
            try:
                try:
                    raise Exception("foo")
                except Exception as exception:
                    raise mock_jwt_exception
            except Exception as exception:
                raise AuthenticationFailed()
        except Exception as exception:
            e = authentication._deepest_jwt_exception(exception)
            assert e == mock_jwt_exception

    def test_jwt_exception_at_the_bottom(self):
        mock_jwt_exception = jwt_exceptions.DecodeError("Not enough segments")
        try:
            try:
                try:
                    raise mock_jwt_exception
                except Exception as exception:
                    raise Exception("foo")
            except Exception as exception:
                raise AuthenticationFailed()
        except Exception as exception:
            e = authentication._deepest_jwt_exception(exception)
            assert e == mock_jwt_exception

    def test_jwt_exception_at_the_top(self):
        mock_jwt_exception = jwt_exceptions.DecodeError("Not enough segments")
        try:
            try:
                try:
                    raise Exception("foo")
                except Exception as exception:
                    raise AuthenticationFailed()
            except Exception as exception:
                raise mock_jwt_exception
        except Exception as exception:
            e = authentication._deepest_jwt_exception(exception)
            assert e == mock_jwt_exception

    def test_multiple_jwt_exceptions(self):
        mock_jwt_exception = jwt_exceptions.DecodeError("Not enough segments")
        try:
            try:
                try:
                    raise Exception("foo")
                except Exception as exception:
                    raise mock_jwt_exception
            except Exception as exception:
                raise jwt_exceptions.InvalidTokenError()
        except Exception as exception:
            e = authentication._deepest_jwt_exception(exception)
            assert e == mock_jwt_exception
