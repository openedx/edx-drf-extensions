"""
Tests for the shared opaque-key URL path converters (edx-platform ADR 0038).

The integration tests pin the behaviour the ADR's "Code examples" section
records as verified: non-deprecated keys resolve and ``reverse()`` round-trips
them, deprecated and malformed keys both 404, and two converters can appear in
one route.
"""
import re
from unittest import TestCase

import pytest
from django.http import HttpResponse
from django.test import SimpleTestCase, override_settings
from django.urls import NoReverseMatch, Resolver404, path, resolve, reverse
from opaque_keys.edx.keys import CourseKey, UsageKey

from edx_rest_framework_extensions.url_converters import (
    CourseKeyConverter,
    UsageKeyConverter,
    register_url_converters,
)


COURSE_KEY = "course-v1:edX+DemoX+Demo_2024"
CCX_KEY = "ccx-v1:edX+DemoX+Demo_2024+ccx@1"
USAGE_KEY = "block-v1:edX+DemoX+Demo_2024+type@problem+block@abc123"
DEPRECATED_COURSE_KEY = "edX/DemoX/Demo_2014"
DEPRECATED_USAGE_KEY = "i4x://edX/DemoX/problem/abc123"


def _dummy_view(request, **kwargs):  # pylint: disable=unused-argument  # pragma: no cover - never called
    return HttpResponse()


# An isolated URLconf exercising the converters, including two in one route.
register_url_converters()

urlpatterns = [
    path(
        "api/course/v1/courses/<course_key:course_key>/",
        _dummy_view,
        name="course_detail",
    ),
    path(
        "api/authoring/v1/xblocks/<usage_key:usage_key>/",
        _dummy_view,
        name="xblock_detail",
    ),
    path(
        "api/course/v1/courses/<course_key:course_key>/blocks/<usage_key:usage_key>/",
        _dummy_view,
        name="course_block_detail",
    ),
]


class CourseKeyConverterTests(TestCase):
    """ Unit tests for CourseKeyConverter. """

    def setUp(self):
        super().setUp()
        self.converter = CourseKeyConverter()

    def test_to_python_parses_course_v1_key(self):
        key = self.converter.to_python(COURSE_KEY)
        self.assertIsInstance(key, CourseKey)
        self.assertEqual(str(key), COURSE_KEY)

    def test_to_python_parses_ccx_key(self):
        # CCX keys are registered by the optional ``ccx-keys`` package (an
        # opaque-keys entry point); the converter accepts whichever key types
        # the host service has installed.
        pytest.importorskip("ccx_keys")
        self.assertIsInstance(self.converter.to_python(CCX_KEY), CourseKey)

    def test_to_python_rejects_malformed_key(self):
        # ValueError → Django treats the route as not matching → 404.
        with pytest.raises(ValueError):
            self.converter.to_python("not-a-course-key")

    def test_to_python_rejects_deprecated_key(self):
        # Org/Course/Run keys are Old Mongo-only and rejected on conforming
        # routes (ADR 0038 rule 9). The '/' means such a key can also never
        # match the regex within a single path segment.
        self.assertTrue(CourseKey.from_string(DEPRECATED_COURSE_KEY).deprecated)
        with pytest.raises(ValueError):
            self.converter.to_python(DEPRECATED_COURSE_KEY)

    def test_to_url_round_trips(self):
        key = CourseKey.from_string(COURSE_KEY)
        self.assertEqual(self.converter.to_url(key), COURSE_KEY)

    def test_regex_excludes_slash(self):
        self.assertIsNone(re.fullmatch(self.converter.regex, DEPRECATED_COURSE_KEY))
        self.assertIsNotNone(re.fullmatch(self.converter.regex, COURSE_KEY))


class UsageKeyConverterTests(TestCase):
    """ Unit tests for UsageKeyConverter. """

    def setUp(self):
        super().setUp()
        self.converter = UsageKeyConverter()

    def test_to_python_parses_block_v1_key(self):
        key = self.converter.to_python(USAGE_KEY)
        self.assertIsInstance(key, UsageKey)
        self.assertEqual(str(key), USAGE_KEY)

    def test_to_python_rejects_malformed_key(self):
        with pytest.raises(ValueError):
            self.converter.to_python("not-a-usage-key")

    def test_to_python_rejects_deprecated_key(self):
        self.assertTrue(UsageKey.from_string(DEPRECATED_USAGE_KEY).deprecated)
        with pytest.raises(ValueError):
            self.converter.to_python(DEPRECATED_USAGE_KEY)

    def test_to_url_round_trips(self):
        key = UsageKey.from_string(USAGE_KEY)
        self.assertEqual(self.converter.to_url(key), USAGE_KEY)


@override_settings(ROOT_URLCONF=__name__)
class UrlConverterIntegrationTests(SimpleTestCase):
    """ resolve()/reverse() behaviour of the registered converters. """

    def test_resolve_passes_parsed_course_key_to_the_view(self):
        match = resolve(f"/api/course/v1/courses/{COURSE_KEY}/")
        self.assertEqual(match.url_name, "course_detail")
        self.assertIsInstance(match.kwargs["course_key"], CourseKey)
        self.assertEqual(str(match.kwargs["course_key"]), COURSE_KEY)

    def test_resolve_passes_parsed_usage_key_to_the_view(self):
        match = resolve(f"/api/authoring/v1/xblocks/{USAGE_KEY}/")
        self.assertEqual(match.url_name, "xblock_detail")
        self.assertIsInstance(match.kwargs["usage_key"], UsageKey)

    def test_two_converters_can_appear_in_one_route(self):
        match = resolve(f"/api/course/v1/courses/{COURSE_KEY}/blocks/{USAGE_KEY}/")
        self.assertEqual(match.url_name, "course_block_detail")
        self.assertIsInstance(match.kwargs["course_key"], CourseKey)
        self.assertIsInstance(match.kwargs["usage_key"], UsageKey)

    def test_malformed_course_key_is_404(self):
        with pytest.raises(Resolver404):
            resolve("/api/course/v1/courses/not-a-course-key/")

    def test_deprecated_usage_key_is_404(self):
        # The deprecated form contains '/', so it cannot even match the
        # single-segment regex; a slashless-but-deprecated spelling is
        # rejected by to_python. Either way: 404.
        with pytest.raises(Resolver404):
            resolve(f"/api/authoring/v1/xblocks/{DEPRECATED_USAGE_KEY}/")

    def test_reverse_round_trips_a_parsed_key(self):
        url = reverse(
            "course_detail",
            kwargs={"course_key": CourseKey.from_string(COURSE_KEY)},
        )
        self.assertEqual(url, f"/api/course/v1/courses/{COURSE_KEY}/")

    def test_reverse_accepts_the_string_form(self):
        url = reverse("xblock_detail", kwargs={"usage_key": USAGE_KEY})
        self.assertEqual(url, f"/api/authoring/v1/xblocks/{USAGE_KEY}/")

    def test_reverse_rejects_a_deprecated_key(self):
        # str(deprecated key) contains '/', which fails the converter regex.
        with pytest.raises(NoReverseMatch):
            reverse(
                "course_detail",
                kwargs={"course_key": CourseKey.from_string(DEPRECATED_COURSE_KEY)},
            )
