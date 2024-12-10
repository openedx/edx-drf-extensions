""" Tests for JWT authentication class. """
from logging import Logger
from unittest import mock

import ddt
from django.contrib.auth import get_user_model
from django.http.cookie import SimpleCookie
from django.test import RequestFactory, TestCase, override_settings
from django.urls import re_path as url_pattern
from django.urls import reverse
from edx_django_utils.cache import RequestCache
from jwt import exceptions as jwt_exceptions
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from edx_rest_framework_extensions.auth.jwt import authentication
from edx_rest_framework_extensions.auth.jwt.authentication import (
    JwtAuthentication,
    JwtAuthenticationError,
    JwtSessionUserMismatchError,
    JwtUserEmailMismatchError,
)
from edx_rest_framework_extensions.auth.jwt.cookies import (
    jwt_cookie_header_payload_name,
    jwt_cookie_name,
    jwt_cookie_signature_name,
)
from edx_rest_framework_extensions.auth.jwt.decoder import jwt_decode_handler
from edx_rest_framework_extensions.auth.jwt.tests.utils import (
    generate_jwt_token,
    generate_latest_version_payload,
)
from edx_rest_framework_extensions.config import (
    ENABLE_JWT_AND_LMS_USER_EMAIL_MATCH,
    ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE,
)
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
    def setUp(self):
        super().setUp()
        RequestCache.clear_all_namespaces()

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
        request.COOKIES[jwt_cookie_name()] = self._get_test_jwt_token()
        drf_request = Request(request)

        assert JwtAuthentication().authenticate(drf_request)

        mock_enforce_csrf.assert_called_with(drf_request)
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'success-cookie')
        set_custom_attribute_keys = [call.args[0] for call in mock_set_custom_attribute.call_args_list]
        assert 'jwt_auth_with_django_request' not in set_custom_attribute_keys

    @mock.patch.object(JwtAuthentication, 'enforce_csrf')
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_with_correct_jwt_cookie_and_django_request(
        self, mock_set_custom_attribute, mock_enforce_csrf
    ):
        """
        Verify authenticate succeeds with a valid JWT cookie and a Django request.

        Note that JwtAuthentication is a DRF class, so a DRF request is expected. However,
        there is custom authentication code that passes in a Django request, so this test
        ensures backward compatibility. A custom attribute has been added to track down this
        custom authentication code.
        """
        request = RequestFactory().post('/')
        request.COOKIES[jwt_cookie_name()] = self._get_test_jwt_token()

        assert JwtAuthentication().authenticate(request)
        mock_enforce_csrf.assert_called_with(request)
        mock_set_custom_attribute.assert_any_call('jwt_auth_with_django_request', True)
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'success-cookie')

    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_csrf_protected(self, mock_set_custom_attribute):
        """
        Ensure authenticate for JWTs properly handles CSRF errors.

        Note: With forgiving JWTs, all JWT cookie exceptions, including CSRF, will
        result in a None so that other authentication classes will also be checked.
        """
        request = RequestFactory().post('/')
        # Set a sample JWT cookie. We mock the auth response but we still want
        # to ensure that there is jwt set because there is other logic that
        # checks for the jwt to be set before moving forward with CSRF checks.
        request.COOKIES[jwt_cookie_name()] = 'foo'
        drf_request = Request(request)

        with mock.patch.object(JSONWebTokenAuthentication, 'authenticate', return_value=('mock-user', "mock-auth")):
            assert JwtAuthentication().authenticate(drf_request) is None
            mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'forgiven-failure')

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
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_jwt_and_session_mismatch(self, mock_set_custom_attribute):
        """ Tests monitoring for JWT cookie when there is a session user mismatch """
        session_user = factories.UserFactory(id=111, username='session-name')
        jwt_user = factories.UserFactory(id=222, username='jwt-name')
        self.client.cookies = SimpleCookie({
            jwt_cookie_name(): self._get_test_jwt_token(user=jwt_user),
        })

        self.client.force_login(session_user)
        response = self.client.get(reverse('authenticated-view'))

        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'success-cookie')
        mock_set_custom_attribute.assert_any_call(
            'jwt_cookie_lms_user_id', jwt_user.id  # pylint: disable=no-member
        )
        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_session_username', session_user.username)
        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_jwt_cookie_username', jwt_user.username)
        assert response.status_code == 200

    @override_settings(
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_jwt_and_session_mismatch_bad_signature_cookie(self, mock_set_custom_attribute):
        """ Tests monitoring for JWT cookie with a bad signature when there is a session user mismatch """
        session_user = factories.UserFactory(id=111, username='session-name')
        jwt_user = factories.UserFactory(id=222, username='jwt-name')
        self.client.cookies = SimpleCookie({
            jwt_cookie_name(): self._get_test_jwt_token(user=jwt_user, is_valid_signature=False),
        })

        self.client.force_login(session_user)
        response = self.client.get(reverse('authenticated-view'))

        mock_set_custom_attribute.assert_any_call(
            'jwt_cookie_lms_user_id', jwt_user.id  # pylint: disable=no-member
        )
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'user-mismatch-failure')
        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_session_username', session_user.username)
        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_jwt_cookie_username', jwt_user.username)
        assert response.status_code == 401

    @override_settings(
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_jwt_and_session_mismatch_invalid_cookie(self, mock_set_custom_attribute):
        """ Tests monitoring for invalid JWT cookie when there is a session user mismatch """
        session_user = factories.UserFactory(id=111, username='session-name')
        self.client.cookies = SimpleCookie({
            jwt_cookie_name(): 'invalid-cookie',
        })

        self.client.force_login(session_user)
        response = self.client.get(reverse('authenticated-view'))

        mock_set_custom_attribute.assert_any_call('jwt_cookie_lms_user_id', None)
        mock_set_custom_attribute.assert_any_call('jwt_cookie_unsafe_decode_issue', 'decode-error')
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'user-mismatch-failure')
        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_session_username', session_user.username)
        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_jwt_cookie_username', None)
        assert response.status_code == 401

    @override_settings(
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

        set_custom_attribute_keys = [call.args[0] for call in mock_set_custom_attribute.call_args_list]
        assert 'jwt_auth_mismatch_session_username' not in set_custom_attribute_keys
        assert 'jwt_auth_mismatch_jwt_cookie_username' not in set_custom_attribute_keys
        assert response.status_code == 200

    @override_settings(
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

        set_custom_attribute_keys = [call.args[0] for call in mock_set_custom_attribute.call_args_list]
        assert 'jwt_auth_mismatch_session_username' not in set_custom_attribute_keys
        assert 'jwt_auth_mismatch_jwt_cookie_username' not in set_custom_attribute_keys
        assert response.status_code == 200

    @override_settings(
        EDX_DRF_EXTENSIONS={
            ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE: True,
        },
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'edx_rest_framework_extensions.auth.jwt.middleware.JwtAuthCookieMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_mismatch_with_set_request_user(self, mock_set_custom_attribute):
        """
        Tests failure for JWT cookie when there is a session user mismatch with a request to set user.

        - This tests coordination between ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE in middleware and JwtAuthentication.
        - This test is kept with the rest of the JWT vs session user tests.
        """
        session_user = factories.UserFactory(id=111, username='session-name')
        jwt_user = factories.UserFactory(id=222, username='jwt-name')
        jwt_header_payload, jwt_signature = self._get_test_jwt_token_payload_and_signature(user=jwt_user)
        # Cookie parts will be recombined by JwtAuthCookieMiddleware
        self.client.cookies = SimpleCookie({
            jwt_cookie_header_payload_name(): jwt_header_payload,
            jwt_cookie_signature_name(): jwt_signature,
        })

        self.client.force_login(session_user)

        response = self.client.get(reverse('authenticated-view'))
        assert response.status_code == 401

        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_session_username', session_user.username)
        mock_set_custom_attribute.assert_any_call('jwt_auth_mismatch_jwt_cookie_username', jwt_user.username)
        mock_set_custom_attribute.assert_any_call(
            'jwt_cookie_lms_user_id', jwt_user.id  # pylint: disable=no-member
        )
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'user-mismatch-enforced-failure')
        mock_set_custom_attribute.assert_any_call(
            'jwt_auth_failed',
            "Exception:JwtSessionUserMismatchError('Failing otherwise successful JWT authentication due "
            "to session user mismatch with set request user.')"
        )

    @override_settings(
        EDX_DRF_EXTENSIONS={
            ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE: True,
        },
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'edx_rest_framework_extensions.auth.jwt.middleware.JwtAuthCookieMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_jwt_and_no_session_and_set_request_user(self, mock_set_custom_attribute):
        """
        Tests success for JWT cookie when there is no session user and there is a request to set user.

        - This tests coordination between ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE in middleware and JwtAuthentication.
        - This test is kept with the rest of the JWT vs session user tests.
        """
        test_user = factories.UserFactory()
        jwt_lms_user_id = 222
        jwt_header_payload, jwt_signature = self._get_test_jwt_token_payload_and_signature(
            user=test_user, lms_user_id=jwt_lms_user_id
        )
        # Cookie parts will be recombined by JwtAuthCookieMiddleware
        self.client.cookies = SimpleCookie({
            jwt_cookie_header_payload_name(): jwt_header_payload,
            jwt_cookie_signature_name(): jwt_signature,
        })

        # unlike other tests, there is no force_login call to start the session
        response = self.client.get(reverse('authenticated-view'))

        mock_set_custom_attribute.assert_any_call('jwt_cookie_lms_user_id', jwt_lms_user_id)
        set_custom_attribute_keys = [call.args[0] for call in mock_set_custom_attribute.call_args_list]
        assert 'jwt_auth_mismatch_session_username' not in set_custom_attribute_keys
        assert 'jwt_auth_mismatch_jwt_cookie_username' not in set_custom_attribute_keys
        assert response.status_code == 200

    @override_settings(
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'edx_rest_framework_extensions.auth.jwt.middleware.JwtAuthCookieMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    def test_authenticate_user_lms_and_jwt_email_mismatch_toggle_disabled(self):
        """
        Test success for JwtAuthentication when ENABLE_JWT_AND_LMS_USER_EMAIL_MATCH is disabled.
        """
        user = factories.UserFactory(email='old@example.com')
        jwt_header_payload, jwt_signature = self._get_test_jwt_token_payload_and_signature(user=user)

        # Cookie parts will be recombined by JwtAuthCookieMiddleware
        self.client.cookies = SimpleCookie({
            jwt_cookie_header_payload_name(): jwt_header_payload,
            jwt_cookie_signature_name(): jwt_signature,
        })

        # simulating email change
        user.email = 'new@example.com'
        user.save()  # pylint: disable=no-member

        self.client.force_login(user)

        response = self.client.get(reverse('authenticated-view'))

        assert response.status_code == 200

    @override_settings(
        EDX_DRF_EXTENSIONS={
            ENABLE_JWT_AND_LMS_USER_EMAIL_MATCH: True,
            'JWT_PAYLOAD_USER_ATTRIBUTE_MAPPING': {},
            'JWT_PAYLOAD_MERGEABLE_USER_ATTRIBUTES': []
        },
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'edx_rest_framework_extensions.auth.jwt.middleware.JwtAuthCookieMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_user_lms_and_jwt_email_match_failure(self, mock_set_custom_attribute):
        """
        Test failure for JwtAuthentication when ENABLE_JWT_AND_LMS_USER_EMAIL_MATCH
        is enabled and the lms and jwt user email do not match.
        """
        user = factories.UserFactory(email='old@example.com')
        jwt_header_payload, jwt_signature = self._get_test_jwt_token_payload_and_signature(user=user)

        # Cookie parts will be recombined by JwtAuthCookieMiddleware
        self.client.cookies = SimpleCookie({
            jwt_cookie_header_payload_name(): jwt_header_payload,
            jwt_cookie_signature_name(): jwt_signature,
        })

        # simulating email change
        user.email = 'new@example.com'
        user.save()  # pylint: disable=no-member

        self.client.force_login(user)

        response = self.client.get(reverse('authenticated-view'))

        assert response.status_code == 401
        mock_set_custom_attribute.assert_any_call(
            'jwt_auth_failed',
            "Exception:JwtUserEmailMismatchError('Failing JWT authentication due to jwt user email mismatch with lms "
            "user email.')"
        )

    @override_settings(
        EDX_DRF_EXTENSIONS={
            ENABLE_JWT_AND_LMS_USER_EMAIL_MATCH: True,
            'JWT_PAYLOAD_USER_ATTRIBUTE_MAPPING': {},
            'JWT_PAYLOAD_MERGEABLE_USER_ATTRIBUTES': []
        },
        MIDDLEWARE=(
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'edx_rest_framework_extensions.auth.jwt.middleware.JwtAuthCookieMiddleware',
        ),
        ROOT_URLCONF='edx_rest_framework_extensions.auth.jwt.tests.test_authentication',
    )
    @mock.patch('edx_rest_framework_extensions.auth.jwt.authentication.set_custom_attribute')
    def test_authenticate_user_lms_and_jwt_email_match_success(self, mock_set_custom_attribute):
        """
        Test success for JwtAuthentication when ENABLE_JWT_AND_LMS_USER_EMAIL_MATCH
        is enabled and the lms and jwt user email match.
        """
        user = factories.UserFactory(email='old@example.com')
        jwt_header_payload, jwt_signature = self._get_test_jwt_token_payload_and_signature(user=user)

        # Cookie parts will be recombined by JwtAuthCookieMiddleware
        self.client.cookies = SimpleCookie({
            jwt_cookie_header_payload_name(): jwt_header_payload,
            jwt_cookie_signature_name(): jwt_signature,
        })

        # Not changing email

        self.client.force_login(user)

        response = self.client.get(reverse('authenticated-view'))

        assert response.status_code == 200
        mock_set_custom_attribute.assert_any_call('jwt_auth_result', 'success-cookie')

    def _get_test_jwt_token(self, user=None, is_valid_signature=True, lms_user_id=None):
        """ Returns a test jwt token for the provided user """
        test_user = factories.UserFactory() if user is None else user
        payload = generate_latest_version_payload(test_user)
        if lms_user_id:
            # In other services, the LMS user id in the JWT would not be the user's id.
            payload['user_id'] = lms_user_id
        if is_valid_signature:
            jwt_token = generate_jwt_token(payload)
        else:
            jwt_token = generate_jwt_token(payload, signing_key='invalid-key')
        return jwt_token

    def _get_test_jwt_token_payload_and_signature(self, user=None, lms_user_id=None):
        """ Returns a test jwt token split into payload and signature """
        jwt_token = self._get_test_jwt_token(user=user, lms_user_id=lms_user_id)
        jwt_token_parts = jwt_token.split('.')
        header_and_payload = '.'.join(jwt_token_parts[0:2])
        signature = jwt_token_parts[2]
        return header_and_payload, signature


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


class JwtAuthenticationErrorTests(TestCase):
    def test_jwt_authentication_error_instance_of_authentication_failed(self):
        # Create an instance of JwtAuthenticationError
        error = JwtAuthenticationError()

        # Assert that it is also an instance of AuthenticationFailed
        self.assertIsInstance(error, AuthenticationFailed)

    def test_jwt_session_user_mismatch_error_instance_of_authentication_failed(self):
        # Create an instance of JwtSessionUserMismatchError
        error = JwtSessionUserMismatchError()

        # Assert that it is also an instance of AuthenticationFailed
        self.assertIsInstance(error, AuthenticationFailed)

    def test_jwt_user_email_mismatch_error_instance_of_authentication_failed(self):
        # Create an instance of JwtUserEmailMismatchError
        error = JwtUserEmailMismatchError()

        # Assert that it is also an instance of AuthenticationFailed
        self.assertIsInstance(error, AuthenticationFailed)
