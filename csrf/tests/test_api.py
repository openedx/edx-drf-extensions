""" Tests for the CSRF API """

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class CsrfTokenTests(APITestCase):
    """ Tests for the CSRF token endpoint. """

    def test_get_token(self):
        """
        Ensure we can get a CSRF token.
        """
        url = reverse('csrf_token')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('csrfToken', response.data)
        self.assertIsNotNone(response.data['csrfToken'])
