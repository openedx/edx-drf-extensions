"""
Test helpers for the Open edX REST API conventions.
"""
from edx_rest_framework_extensions.errors import ERROR_TYPE_BASE_URI, error_type_uri


#: The keys every ADR 0029 error envelope must carry.
REQUIRED_ERROR_ENVELOPE_FIELDS = ("type", "title", "status", "detail", "instance")

#: Legacy edx-platform error keys (``DeveloperErrorViewMixin``) that must not
#: leak into a standardized envelope.
LEGACY_ERROR_FIELDS = ("developer_message", "error_code")


def assert_error_envelope(response, expected_status=None, expected_type_slug=None):
    """
    Assert that ``response`` carries a well-formed ADR 0029 error envelope.

    Checks that every required envelope field is present, that ``status``
    inside the body matches the response's status code, that ``type`` is an
    ``https://docs.openedx.org/errors/`` URI, that ``instance`` is the request
    path (when the test client attached the request to the response), and that
    no legacy ``DeveloperErrorViewMixin`` fields leak through.

    Arguments:
        response: a DRF test-client response (``response.data``) or any
            response exposing ``json()``.
        expected_status (int): when given, also assert the HTTP status code.
        expected_type_slug (str): when given, also assert the exact error-type
            slug (e.g. ``"authn"``, ``"not-found"``).

    Returns:
        dict: the decoded envelope, for any follow-up assertions.
    """
    if expected_status is not None:
        assert response.status_code == expected_status, (
            f"expected HTTP {expected_status}, got {response.status_code}"
        )

    data = getattr(response, "data", None)
    if data is None:
        data = response.json()

    for field in REQUIRED_ERROR_ENVELOPE_FIELDS:
        assert field in data, f"ADR 0029: missing envelope field '{field}' in {data!r}"

    assert data["status"] == response.status_code, (
        f"ADR 0029: envelope 'status' {data['status']!r} does not match "
        f"response status {response.status_code}"
    )
    assert str(data["type"]).startswith(ERROR_TYPE_BASE_URI), (
        f"ADR 0029: 'type' {data['type']!r} is not an {ERROR_TYPE_BASE_URI} URI"
    )
    if expected_type_slug is not None:
        assert data["type"] == error_type_uri(expected_type_slug), (
            f"ADR 0029: expected type '{error_type_uri(expected_type_slug)}', got {data['type']!r}"
        )

    wsgi_request = getattr(response, "wsgi_request", None)
    if wsgi_request is not None:
        assert data["instance"] == wsgi_request.path, (
            f"ADR 0029: 'instance' {data['instance']!r} is not the request path {wsgi_request.path!r}"
        )

    for field in LEGACY_ERROR_FIELDS:
        assert field not in data, f"ADR 0029: legacy field '{field}' must not appear in the envelope"

    return data
