""" Tests for the ADR 0029 standardized error-response building blocks. """
from django.test import TestCase, override_settings
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from edx_rest_framework_extensions import errors
from edx_rest_framework_extensions.errors import (
    ERROR_TYPE_BASE_URI,
    Conflict,
    ErrorResponseSerializer,
    classify_error,
    error_type_uri,
    flatten_detail,
    normalize_validation_errors,
    register_error_type,
    standardized_error_exception_handler,
)
from edx_rest_framework_extensions.mixins import StandardizedErrorMixin


_REQUIRED_ENVELOPE_FIELDS = ("type", "title", "status", "detail", "instance")


def _get_response_for(exc, path="/api/things/"):
    """ Run ``exc`` through a StandardizedErrorMixin APIView and return the response. """

    class _View(StandardizedErrorMixin, APIView):
        # An authenticator with a WWW-Authenticate challenge, so DRF keeps
        # NotAuthenticated/AuthenticationFailed at 401 instead of downgrading to 403.
        authentication_classes = (BasicAuthentication,)
        permission_classes = ()

        def get(self, request):
            raise exc

    return _View.as_view()(APIRequestFactory().get(path))


def _custom_base_handler(exc, context):  # pylint: disable=unused-argument
    """ A settings-resolvable base handler used by the dependency-inversion tests. """
    return Response({"detail": "handled by custom base"}, status=418)


class StandardizedErrorHandlerEnvelopeTests(TestCase):
    """ The envelope produced for each cataloged exception type. """

    def _assert_envelope(self, response, expected_status, expected_slug, expected_title):
        for field in _REQUIRED_ENVELOPE_FIELDS:
            self.assertIn(field, response.data)
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response.data["status"], expected_status)
        self.assertEqual(response.data["type"], error_type_uri(expected_slug))
        self.assertEqual(response.data["title"], expected_title)
        self.assertEqual(response.data["instance"], "/api/things/")
        self.assertEqual(response["Content-Type"], "application/json")

    def test_not_authenticated(self):
        response = _get_response_for(NotAuthenticated())
        self._assert_envelope(response, 401, "authn", "Authentication Required")

    def test_authentication_failed(self):
        response = _get_response_for(AuthenticationFailed())
        self._assert_envelope(response, 401, "authn", "Authentication Failed")

    def test_permission_denied(self):
        response = _get_response_for(PermissionDenied())
        self._assert_envelope(response, 403, "authz", "Permission Denied")

    def test_not_found(self):
        response = _get_response_for(NotFound("no such thing"))
        self._assert_envelope(response, 404, "not-found", "Not Found")
        self.assertEqual(response.data["detail"], "no such thing")

    def test_validation_error(self):
        response = _get_response_for(ValidationError({"name": ["required"]}))
        self._assert_envelope(response, 400, "validation", "Validation Error")
        self.assertEqual(response.data["errors"], {"name": ["required"]})

    def test_throttled(self):
        response = _get_response_for(Throttled())
        self._assert_envelope(response, 429, "rate-limited", "Too Many Requests")

    def test_conflict(self):
        response = _get_response_for(Conflict())
        self._assert_envelope(response, 409, "conflict", "Conflict")

    def test_cataloged_exception_subclass_inherits_slug_and_title(self):
        class _MoreSpecificNotFound(NotFound):
            pass

        response = _get_response_for(_MoreSpecificNotFound())
        self._assert_envelope(response, 404, "not-found", "Not Found")

    def test_uncataloged_api_exception_is_internal(self):
        response = _get_response_for(APIException())
        self._assert_envelope(response, 500, "internal", "Internal Server Error")

    def test_non_api_exception_yields_internal_envelope(self):
        # DRF's base handler returns None for non-APIExceptions; the
        # standardized handler still produces the internal 500 envelope.
        response = _get_response_for(RuntimeError("boom"))
        for field in _REQUIRED_ENVELOPE_FIELDS:
            self.assertIn(field, response.data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["type"], error_type_uri("internal"))
        self.assertEqual(response.data["instance"], "/api/things/")

    def test_user_message_passthrough(self):
        exc = NotFound("no such thing")
        exc.user_message = "We could not find that."
        response = _get_response_for(exc)
        self.assertEqual(response.data["user_message"], "We could not find that.")

    def test_no_user_message_key_when_absent(self):
        response = _get_response_for(NotFound())
        self.assertNotIn("user_message", response.data)

    def test_no_legacy_fields(self):
        response = _get_response_for(NotFound())
        self.assertNotIn("developer_message", response.data)
        self.assertNotIn("error_code", response.data)


class BaseHandlerDependencyInversionTests(TestCase):
    """ The STANDARDIZED_ERROR_BASE_HANDLER setting controls the delegate handler. """

    @override_settings(EDX_DRF_EXTENSIONS={
        "STANDARDIZED_ERROR_BASE_HANDLER":
            "edx_rest_framework_extensions.tests.test_errors._custom_base_handler",
    })
    def test_dotted_path_base_handler(self):
        response = _get_response_for(NotFound())
        # The custom base handler supplied the status; the envelope reshaping
        # still ran on top of its response.
        self.assertEqual(response.status_code, 418)
        self.assertEqual(response.data["detail"], "handled by custom base")
        self.assertEqual(response.data["type"], error_type_uri("not-found"))

    @override_settings(EDX_DRF_EXTENSIONS={
        "STANDARDIZED_ERROR_BASE_HANDLER": _custom_base_handler,
    })
    def test_callable_base_handler(self):
        response = _get_response_for(NotFound())
        self.assertEqual(response.status_code, 418)
        self.assertEqual(response.data["detail"], "handled by custom base")

    def test_defaults_to_drf_handler(self):
        response = _get_response_for(NotFound("gone"))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "gone")


class ErrorTypeCatalogTests(TestCase):
    """ error_type_uri, classify_error, and the register_error_type extension helper. """

    def test_error_type_uri(self):
        self.assertEqual(error_type_uri("authn"), ERROR_TYPE_BASE_URI + "authn")

    def test_classify_unknown_exception(self):
        self.assertEqual(classify_error(RuntimeError()), ("internal", "Internal Server Error"))

    def test_register_error_type(self):
        class Teapot(APIException):
            status_code = 418
            default_detail = "I'm a teapot."

        registry_snapshot = list(errors._registered_error_types)  # pylint: disable=protected-access
        try:
            register_error_type(Teapot, "teapot", "I'm a Teapot")
            self.assertEqual(classify_error(Teapot()), ("teapot", "I'm a Teapot"))

            response = _get_response_for(Teapot())
            self.assertEqual(response.status_code, 418)
            self.assertEqual(response.data["type"], error_type_uri("teapot"))
            self.assertEqual(response.data["title"], "I'm a Teapot")
        finally:
            errors._registered_error_types[:] = registry_snapshot  # pylint: disable=protected-access

    def test_registration_takes_precedence_over_builtin_catalog(self):
        class SpecialNotFound(NotFound):
            pass

        registry_snapshot = list(errors._registered_error_types)  # pylint: disable=protected-access
        try:
            register_error_type(SpecialNotFound, "special-not-found", "Special Not Found")
            self.assertEqual(classify_error(SpecialNotFound()), ("special-not-found", "Special Not Found"))
            # The cataloged base class is unaffected.
            self.assertEqual(classify_error(NotFound()), ("not-found", "Not Found"))
        finally:
            errors._registered_error_types[:] = registry_snapshot  # pylint: disable=protected-access


class EnvelopeFormatterTests(TestCase):
    """ flatten_detail and normalize_validation_errors. """

    def test_flatten_string(self):
        self.assertEqual(flatten_detail("oops"), "oops")

    def test_flatten_dict_with_detail(self):
        self.assertEqual(flatten_detail({"detail": "oops"}), "oops")

    def test_flatten_list(self):
        self.assertEqual(flatten_detail(["first", "second"]), "first")

    def test_flatten_other(self):
        self.assertEqual(flatten_detail({"name": ["bad"]}), "{'name': ['bad']}")

    def test_normalize_dict(self):
        self.assertEqual(
            normalize_validation_errors({"name": ["a", "b"], "age": "c"}),
            {"name": ["a", "b"], "age": ["c"]},
        )

    def test_normalize_list(self):
        self.assertEqual(normalize_validation_errors(["a"]), {"non_field_errors": ["a"]})

    def test_normalize_scalar(self):
        self.assertEqual(normalize_validation_errors("a"), {"non_field_errors": ["a"]})


class ErrorResponseSerializerTests(TestCase):
    """ The plain-DRF documentation serializer round-trips a real envelope. """

    def test_serializes_full_envelope(self):
        response = _get_response_for(ValidationError({"name": ["required"]}))
        serializer = ErrorResponseSerializer(data=dict(response.data))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_optional_fields_are_optional(self):
        serializer = ErrorResponseSerializer(data={
            "type": error_type_uri("internal"),
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred.",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)


class HandlerWithoutRequestContextTests(TestCase):
    """ The handler tolerates a context with no request (no 'instance' key). """

    def test_no_request_in_context(self):
        response = standardized_error_exception_handler(NotFound(), {"request": None})
        self.assertNotIn("instance", response.data)
        self.assertEqual(response.data["type"], error_type_uri("not-found"))
