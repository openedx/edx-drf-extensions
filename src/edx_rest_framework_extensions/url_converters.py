"""
Shared opaque-key URL path converters (edx-platform ADR 0038).

edx-platform ADR 0038 ("Standardize REST API URL Structure") rule 9 requires
identifiers on conforming API URLs to be opaque keys resolved by shared path
converters, so that views receive parsed keys and a malformed key becomes a
consistent 404 rather than an ad-hoc 400::

    # urls.py — once per service, before any pattern using the converters
    from edx_rest_framework_extensions.url_converters import register_url_converters
    register_url_converters()

    urlpatterns = [
        path(
            "api/course/v1/courses/<course_key:course_key>/",
            CourseView.as_view(),
            name="course_detail",
        ),
    ]

New and migrated APIs accept only non-deprecated keys (``course-v1:``,
``ccx-v1:``, ``block-v1:`` …). Deprecated ``Org/Course/Run`` and ``i4x://``
forms contain ``/`` and exist only for pre-existing Old Mongo content, which
conforming routes do not serve; the converters reject them in ``to_python``,
which Django turns into a 404. Because only non-deprecated keys are accepted,
the regex is simply "no slash" rather than a transcription of the permissive
platform patterns — endpoints that must keep serving Old Mongo content should
keep their slash-tolerant ``re_path`` routes (or, for router-registered
ViewSets, the :mod:`~edx_rest_framework_extensions.routers` lookup regexes)
instead of these converters.
"""

from django.urls import register_converter
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey


class CourseKeyConverter:
    """
    Match non-deprecated course run keys (``course-v1:``, ``ccx-v1:``).

    Views receive a parsed :class:`~opaque_keys.edx.keys.CourseKey`;
    ``reverse()`` accepts a ``CourseKey`` (or its string form).
    """

    regex = r'[^/]+'

    def to_python(self, value: str) -> CourseKey:
        """ Parse ``value``; raise ``ValueError`` (→ 404) if invalid or deprecated. """
        try:
            course_key = CourseKey.from_string(value)
        except InvalidKeyError as exc:
            raise ValueError from exc          # Django turns this into a 404
        if course_key.deprecated:              # Org/Course/Run — Old Mongo only
            raise ValueError(f"deprecated course key: {value}")
        return course_key

    def to_url(self, value: CourseKey) -> str:
        """ Serialize for ``reverse()``. """
        return str(value)


class UsageKeyConverter:
    """
    Match non-deprecated usage keys (``block-v1:``, ``lb:``, …).

    Views receive a parsed :class:`~opaque_keys.edx.keys.UsageKey`;
    ``reverse()`` accepts a ``UsageKey`` (or its string form).
    """

    regex = r'[^/]+'

    def to_python(self, value: str) -> UsageKey:
        """ Parse ``value``; raise ``ValueError`` (→ 404) if invalid or deprecated. """
        try:
            usage_key = UsageKey.from_string(value)
        except InvalidKeyError as exc:
            raise ValueError from exc          # Django turns this into a 404
        if usage_key.deprecated:               # i4x:// — Old Mongo only
            raise ValueError(f"deprecated usage key: {value}")
        return usage_key

    def to_url(self, value: UsageKey) -> str:
        """ Serialize for ``reverse()``. """
        return str(value)


def register_url_converters():
    """
    Register the shared converters under the names ``course_key`` and
    ``usage_key``. Call once per service, from the project URLconf, before
    any URL pattern that uses ``<course_key:...>`` or ``<usage_key:...>``.
    """
    register_converter(CourseKeyConverter, "course_key")
    register_converter(UsageKeyConverter, "usage_key")
