""" Tests for the CSRF API """

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from edx_rest_framework_extensions.auth.jwt.tests.utils import generate_jwt
from edx_rest_framework_extensions.tests.factories import UserFactory


class CsrfTokenTests(APITestCase):
    """ Tests for the CSRF token endpoint. """

    def test_get_token(self):
        """
        Ensure we can get a CSRF token.
        """
        url = reverse('csrf_token')
        user = UserFactory()
        jwt = generate_jwt(user)
        self.client.credentials(HTTP_AUTHORIZATION='JWT {}'.format(jwt))
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('csrfToken', response.data)
