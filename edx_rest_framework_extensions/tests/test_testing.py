""" Tests for the REST API convention test helpers. """
from types import SimpleNamespace
from unittest import TestCase

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from edx_rest_framework_extensions.errors import error_type_uri
from edx_rest_framework_extensions.mixins import StandardizedErrorMixin
from edx_rest_framework_extensions.testing import assert_error_envelope


def _real_envelope_response(exc, path="/api/things/"):
    """ Produce a real envelope response through a StandardizedErrorMixin view. """

    class _View(StandardizedErrorMixin, APIView):
        authentication_classes = ()
        permission_classes = ()

        def get(self, request):
            raise exc

    return _View.as_view()(APIRequestFactory().get(path))


def _fake_response(data, status_code=404, **attrs):
    """ Build a minimal response-like object carrying ``data``. """
    return SimpleNamespace(data=data, status_code=status_code, **attrs)


class AssertErrorEnvelopeTests(TestCase):
    """ Tests for assert_error_envelope(). """

    def test_passes_on_real_envelope(self):
        response = _real_envelope_response(NotFound("gone"))
        data = assert_error_envelope(response, expected_status=404, expected_type_slug="not-found")
        self.assertEqual(data["detail"], "gone")

    def test_passes_on_validation_envelope(self):
        response = _real_envelope_response(ValidationError({"name": ["required"]}))
        data = assert_error_envelope(response, expected_status=400, expected_type_slug="validation")
        self.assertEqual(data["errors"], {"name": ["required"]})

    def test_fails_on_wrong_status(self):
        response = _real_envelope_response(NotFound())
        with self.assertRaisesRegex(AssertionError, "expected HTTP 401"):
            assert_error_envelope(response, expected_status=401)

    def test_fails_on_wrong_type_slug(self):
        response = _real_envelope_response(NotFound())
        with self.assertRaisesRegex(AssertionError, "expected type"):
            assert_error_envelope(response, expected_type_slug="authz")

    def test_fails_on_missing_required_field(self):
        response = _fake_response({
            "type": error_type_uri("not-found"),
            "title": "Not Found",
            "status": 404,
            "detail": "gone",
            # no "instance"
        })
        with self.assertRaisesRegex(AssertionError, "missing envelope field 'instance'"):
            assert_error_envelope(response)

    def test_fails_on_status_mismatch_between_body_and_response(self):
        response = _fake_response(
            {"type": error_type_uri("not-found"), "title": "x", "status": 400,
             "detail": "d", "instance": "/p"},
            status_code=404,
        )
        with self.assertRaisesRegex(AssertionError, "does not match"):
            assert_error_envelope(response)

    def test_fails_on_non_catalog_type_uri(self):
        response = _fake_response(
            {"type": "https://example.com/errors/other", "title": "x", "status": 404,
             "detail": "d", "instance": "/p"},
            status_code=404,
        )
        with self.assertRaisesRegex(AssertionError, "is not an"):
            assert_error_envelope(response)

    def test_fails_on_legacy_fields(self):
        response = _fake_response(
            {"type": error_type_uri("not-found"), "title": "x", "status": 404,
             "detail": "d", "instance": "/p", "developer_message": "leak"},
            status_code=404,
        )
        with self.assertRaisesRegex(AssertionError, "legacy field 'developer_message'"):
            assert_error_envelope(response)

    def test_fails_on_instance_not_matching_request_path(self):
        response = _fake_response(
            {"type": error_type_uri("not-found"), "title": "x", "status": 404,
             "detail": "d", "instance": "/other/"},
            status_code=404,
            wsgi_request=SimpleNamespace(path="/api/things/"),
        )
        with self.assertRaisesRegex(AssertionError, "is not the request path"):
            assert_error_envelope(response)

    def test_falls_back_to_json_method(self):
        body = {"type": error_type_uri("authn"), "title": "Authentication Required",
                "status": 401, "detail": "d", "instance": "/p"}
        response = SimpleNamespace(status_code=401, json=lambda: body)
        data = assert_error_envelope(response, expected_type_slug="authn")
        self.assertEqual(data, body)
