"""
Opaque-key ``lookup_value_regex`` constants for DRF routers.

DRF's routers default a ViewSet's ``lookup_value_regex`` to ``[^/.]+``, which
cannot match Open edX opaque keys: old-style course keys contain slashes
(``edX/DemoX/Demo_2014``) and new-style keys contain dots in the run or block
id. Every router-registered ViewSet keyed by an opaque key therefore needs an
explicit ``lookup_value_regex``, and edx-platform's pilot APIs each hand-wrote
their own. These constants are the shared spellings, matching the patterns
``openedx/core/constants.py`` has used in URL routes for years (with capturing
groups made non-capturing, as router regexes are embedded inside the named
lookup group)::

    class CourseDetailsViewSet(viewsets.GenericViewSet):
        lookup_field = "course_key"
        lookup_value_regex = COURSE_KEY_LOOKUP_REGEX

The patterns are deliberately permissive — they delimit the key within the URL
path; real validation belongs to ``opaque_keys`` (``CourseKey.from_string`` /
``UsageKey.from_string``) in the view.
"""

#: Matches new-style (``course-v1:org+course+run``) and old-style
#: (``org/course/run``) course keys.
COURSE_KEY_LOOKUP_REGEX = r"[^/+]+(?:/|\+)[^/+]+(?:/|\+)[^/?]+"

#: Matches new-style (``block-v1:...+type@...+block@...``) and old-style
#: (``i4x://org/course/category/name``) usage keys.
USAGE_KEY_LOOKUP_REGEX = r"(?:i4x://?[^/]+/[^/]+/[^/]+/[^@]+(?:@[^/]+)?)|(?:[^/]+)"
