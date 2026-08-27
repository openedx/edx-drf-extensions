"""
Standardized error responses for Open edX REST APIs (ADR 0029).

This module is the reusable core of edx-platform's
``docs/decisions/0029-standardize-error-responses`` implementation: a DRF
exception handler that reshapes error responses into a single JSON envelope,
the building blocks it is made of, and a plain-DRF serializer that documents
the envelope in OpenAPI schemas.

The envelope shape is::

    {
        "type":     "https://docs.openedx.org/errors/<slug>",
        "title":    "<Human-readable title>",
        "status":   <HTTP status code>,
        "detail":   "<flattened error message>",
        "instance": "<request path>"
    }

with two optional keys: ``user_message`` (when the raised exception carries a
``user_message`` attribute) and ``errors`` (per-field details, on
``ValidationError`` only).

Wiring options:

* Per view — mix :class:`~edx_rest_framework_extensions.mixins.StandardizedErrorMixin`
  into the view (or use it via a base class).
* Service-wide — point DRF at the handler directly::

      REST_FRAMEWORK = {
          "EXCEPTION_HANDLER":
              "edx_rest_framework_extensions.errors.standardized_error_exception_handler",
      }

Dependency inversion — the handler delegates to a *base* exception handler
before shaping the envelope, so services can keep their own error-monitoring
behavior. It defaults to DRF's own ``exception_handler``; override it with the
``STANDARDIZED_ERROR_BASE_HANDLER`` key of the ``EDX_DRF_EXTENSIONS`` setting
(a dotted path or a callable). edx-platform, for example, sets::

    EDX_DRF_EXTENSIONS = {
        "STANDARDIZED_ERROR_BASE_HANDLER":
            "openedx.core.lib.request_utils.ignored_error_exception_handler",
    }
"""
from django.utils.module_loading import import_string
from rest_framework import serializers
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
from rest_framework.views import exception_handler as drf_exception_handler

from edx_rest_framework_extensions.settings import get_setting


# ---------------------------------------------------------------------------
# Error-type URI catalog
# ---------------------------------------------------------------------------

#: Base URI under which every ADR 0029 error-type slug is published.
ERROR_TYPE_BASE_URI = "https://docs.openedx.org/errors/"


def error_type_uri(slug):
    """Return the full ADR 0029 error-type URI for ``slug`` (e.g. ``"authn"``)."""
    return ERROR_TYPE_BASE_URI + slug


class Conflict(APIException):
    """HTTP 409 Conflict — ADR 0029."""

    status_code = 409
    default_detail = "A conflict occurred."
    default_code = "conflict"


# The built-in catalog, checked in order with ``isinstance`` so subclasses of a
# cataloged exception inherit its slug and title. ``NotAuthenticated`` and
# ``AuthenticationFailed`` share the "authn" slug but carry distinct titles.
_BUILTIN_ERROR_TYPES = (
    (NotAuthenticated, "authn", "Authentication Required"),
    (AuthenticationFailed, "authn", "Authentication Failed"),
    (PermissionDenied, "authz", "Permission Denied"),
    (NotFound, "not-found", "Not Found"),
    (ValidationError, "validation", "Validation Error"),
    (Throttled, "rate-limited", "Too Many Requests"),
    (Conflict, "conflict", "Conflict"),
)

# Extension registrations, most recent first. Checked before the built-ins so
# a registration can also specialize a cataloged exception's subclass.
_registered_error_types = []

#: Slug and title used when an exception matches nothing in the catalog.
INTERNAL_ERROR_SLUG = "internal"
INTERNAL_ERROR_TITLE = "Internal Server Error"


def register_error_type(exception_class, slug, title):
    """
    Extend the ADR 0029 error-type catalog with a custom exception class.

    After registration, any raised instance of ``exception_class`` (or a
    subclass) is enveloped with ``type`` ``error_type_uri(slug)`` and ``title``
    ``title``. Registrations are consulted most-recent-first and take
    precedence over the built-in catalog, so registering a subclass of a
    cataloged exception specializes it.

    Arguments:
        exception_class (type): the exception class to classify.
        slug (str): the error-type slug, appended to :data:`ERROR_TYPE_BASE_URI`.
        title (str): the human-readable envelope title.
    """
    _registered_error_types.insert(0, (exception_class, slug, title))


def classify_error(exc):
    """
    Return the ``(slug, title)`` catalog entry for the exception ``exc``.

    Falls back to ``(INTERNAL_ERROR_SLUG, INTERNAL_ERROR_TITLE)`` when the
    exception matches neither a registered nor a built-in catalog entry.
    """
    for exception_class, slug, title in tuple(_registered_error_types) + _BUILTIN_ERROR_TYPES:
        if isinstance(exc, exception_class):
            return slug, title
    return INTERNAL_ERROR_SLUG, INTERNAL_ERROR_TITLE


# ---------------------------------------------------------------------------
# Envelope formatters
# ---------------------------------------------------------------------------

def flatten_detail(data):
    """Extract a single string detail message from a DRF response data payload."""
    if isinstance(data, str):
        return data
    if isinstance(data, dict) and "detail" in data:
        return str(data["detail"])
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data)


def normalize_validation_errors(detail):
    """Convert DRF validation error detail into a consistent per-field dict."""
    if isinstance(detail, dict):
        return {
            field: [str(e) for e in (errs if isinstance(errs, list) else [errs])]
            for field, errs in detail.items()
        }
    if isinstance(detail, list):
        return {"non_field_errors": [str(e) for e in detail]}
    return {"non_field_errors": [str(detail)]}


def build_error_envelope(exc, response, request=None):
    """
    Build the ADR 0029 error envelope for ``exc``.

    Arguments:
        exc (Exception): the exception the view raised.
        response (rest_framework.response.Response): the response produced by
            the base exception handler; supplies the status code and the raw
            error data that ``detail`` is flattened from.
        request: the request being handled, if available; supplies ``instance``.

    Returns:
        dict: the envelope, ready to be assigned to ``response.data``.
    """
    slug, title = classify_error(exc)
    body = {
        "type": error_type_uri(slug),
        "title": title,
        "status": response.status_code,
        "detail": flatten_detail(response.data),
    }
    if request:
        body["instance"] = request.path
    if hasattr(exc, "user_message") and exc.user_message:
        body["user_message"] = exc.user_message
    if isinstance(exc, ValidationError) and hasattr(exc, "detail"):
        body["errors"] = normalize_validation_errors(exc.detail)
    return body


# ---------------------------------------------------------------------------
# Exception handler (with the base-handler dependency inversion)
# ---------------------------------------------------------------------------

def _base_exception_handler():
    """
    Resolve the exception handler this one delegates to before shaping the envelope.

    Defaults to DRF's ``exception_handler``. Services override it with the
    ``STANDARDIZED_ERROR_BASE_HANDLER`` key of the ``EDX_DRF_EXTENSIONS``
    setting — either a dotted import path or a callable — to keep their own
    error-monitoring behavior in the loop.
    """
    handler = get_setting("STANDARDIZED_ERROR_BASE_HANDLER")
    if handler is None:
        return drf_exception_handler
    if callable(handler):
        return handler
    return import_string(handler)


def standardized_error_exception_handler(exc, context):
    """
    ADR 0029 — DRF exception handler returning the standardized error envelope.

    Delegates to the base handler (see :func:`_base_exception_handler`) and
    reformats its response via :func:`build_error_envelope`. When the base
    handler declines to handle the exception (returns ``None``, DRF's behavior
    for non-``APIException`` errors), a generic ``internal`` 500 envelope is
    returned instead of re-raising.
    """
    response = _base_exception_handler()(exc, context)
    request = context.get("request")

    if response is None:
        body = {
            "type": error_type_uri(INTERNAL_ERROR_SLUG),
            "title": INTERNAL_ERROR_TITLE,
            "status": 500,
            "detail": "An unexpected error occurred. Please try again later.",
        }
        if request:
            body["instance"] = request.path
        return Response(body, status=500)

    response.data = build_error_envelope(exc, response, request=request)
    response["Content-Type"] = "application/json"
    return response


# ---------------------------------------------------------------------------
# OpenAPI documentation serializer
# ---------------------------------------------------------------------------

class ErrorResponseSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Plain-DRF serializer describing the ADR 0029 error envelope.

    Intended for OpenAPI response declarations so error responses are
    documented with their real shape, e.g. with drf-spectacular::

        @extend_schema(responses={
            200: MyResourceSerializer,
            404: ErrorResponseSerializer,
        })

    It is a documentation serializer: nothing deserializes through it, so it
    implements no ``create``/``update``.
    """

    type = serializers.URLField(
        help_text="Error-type URI (https://docs.openedx.org/errors/<slug>).",
    )
    title = serializers.CharField(help_text="Human-readable error title.")
    status = serializers.IntegerField(help_text="HTTP status code, repeated from the response.")
    detail = serializers.CharField(help_text="Flattened human-readable error message.")
    instance = serializers.CharField(
        required=False,
        help_text="Path of the request that produced the error.",
    )
    user_message = serializers.CharField(
        required=False,
        help_text="End-user-facing message, when the raising code supplied one.",
    )
    errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
        help_text="Per-field validation errors (validation errors only).",
    )
