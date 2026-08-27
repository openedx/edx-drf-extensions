""" Tests for the opaque-key lookup regex constants. """
import re
from unittest import TestCase

import ddt

from edx_rest_framework_extensions.routers import (
    COURSE_KEY_LOOKUP_REGEX,
    USAGE_KEY_LOOKUP_REGEX,
)


@ddt.ddt
class CourseKeyLookupRegexTests(TestCase):
    """ COURSE_KEY_LOOKUP_REGEX delimits both course-key styles. """

    @ddt.data(
        "course-v1:edX+DemoX+Demo_2024",       # new style
        "course-v1:edX+DemoX+Demo_2024.1",     # dot in the run
        "edX/DemoX/Demo_2014",                 # old style
        "ccx-v1:edX+DemoX+Demo_2024+ccx@1",    # CCX key
    )
    def test_matches(self, value):
        self.assertIsNotNone(re.fullmatch(COURSE_KEY_LOOKUP_REGEX, value))

    @ddt.data(
        "edX",              # no separators at all
        "edX+DemoX",        # only one separator
        "a/b/c/d",          # trailing slash-separated extra segment
        "a+b+c?x=1",        # query separator inside the run
    )
    def test_rejects(self, value):
        self.assertIsNone(re.fullmatch(COURSE_KEY_LOOKUP_REGEX, value))


@ddt.ddt
class UsageKeyLookupRegexTests(TestCase):
    """ USAGE_KEY_LOOKUP_REGEX delimits both usage-key styles. """

    @ddt.data(
        "block-v1:edX+DemoX+Demo_2024+type@problem+block@abc123",  # new style
        "lb:edX:DemoX:problem:abc123",                             # learning-core style
        "i4x://edX/DemoX/problem/abc123",                          # old style
        "i4x://edX/DemoX/problem/abc123@draft",                    # old style with revision
    )
    def test_matches(self, value):
        self.assertIsNotNone(re.fullmatch(USAGE_KEY_LOOKUP_REGEX, value))

    @ddt.data(
        "edX/DemoX/problem",     # bare slashes without the i4x prefix
        "",                      # empty
    )
    def test_rejects(self, value):
        self.assertIsNone(re.fullmatch(USAGE_KEY_LOOKUP_REGEX, value))
