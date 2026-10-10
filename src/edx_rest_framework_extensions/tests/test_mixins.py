""" Tests for the DRF view mixins. """
from django.test import TestCase
from rest_framework.exceptions import NotFound
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from edx_rest_framework_extensions.errors import (
    error_type_uri,
    standardized_error_exception_handler,
)
from edx_rest_framework_extensions.mixins import StandardizedErrorMixin


class StandardizedErrorMixinTests(TestCase):
    """ Tests for StandardizedErrorMixin. """

    def test_get_exception_handler_returns_standardized_handler(self):
        class _View(StandardizedErrorMixin, APIView):
            pass

        self.assertIs(_View().get_exception_handler(), standardized_error_exception_handler)

    def test_view_scoping(self):
        """ Only views carrying the mixin return the envelope. """

        class _EnvelopedView(StandardizedErrorMixin, APIView):
            authentication_classes = ()
            permission_classes = ()

            def get(self, request):
                raise NotFound()

        class _PlainView(APIView):
            authentication_classes = ()
            permission_classes = ()

            def get(self, request):
                raise NotFound()

        request = APIRequestFactory().get("/api/things/")

        enveloped = _EnvelopedView.as_view()(request)
        self.assertEqual(enveloped.data["type"], error_type_uri("not-found"))

        plain = _PlainView.as_view()(request)
        self.assertNotIn("type", plain.data)
        self.assertNotIn("instance", plain.data)
