""" Tests for the ADR 0036 response-shaping helpers. """
from unittest import TestCase
from unittest.mock import Mock

from django.core.exceptions import ImproperlyConfigured

from edx_rest_framework_extensions.shaping import MinimalViewMixin, project


class ProjectTests(TestCase):
    """ Tests for project(). """

    def setUp(self):
        super().setUp()
        self.data = {"id": 1, "name": "thing", "children": [2, 3], "heavy": {"x": 1}}

    def test_csv_string(self):
        self.assertEqual(project(self.data, "id,name"), {"id": 1, "name": "thing"})

    def test_iterable(self):
        self.assertEqual(project(self.data, ["id", "heavy"]), {"id": 1, "heavy": {"x": 1}})

    def test_whitespace_and_empty_names_ignored(self):
        self.assertEqual(project(self.data, " id , ,name "), {"id": 1, "name": "thing"})

    def test_dotted_paths_stripped_to_first_segment(self):
        self.assertEqual(project(self.data, "children.x"), {"children": [2, 3]})

    def test_unknown_fields_yield_empty_dict(self):
        self.assertEqual(project(self.data, "nope"), {})

    def test_falsy_fields_returns_data_unchanged(self):
        self.assertIs(project(self.data, None), self.data)
        self.assertIs(project(self.data, ""), self.data)
        self.assertIs(project(self.data, []), self.data)

    def test_only_whitespace_names_returns_data_unchanged(self):
        self.assertIs(project(self.data, " , "), self.data)

    def test_non_dict_data_returned_untouched(self):
        self.assertEqual(project([1, 2], "id"), [1, 2])
        self.assertEqual(project("text", "id"), "text")

    def test_returns_new_dict(self):
        result = project(self.data, "id,name,children,heavy")
        self.assertEqual(result, self.data)
        self.assertIsNot(result, self.data)


class MinimalViewMixinTests(TestCase):
    """ Tests for MinimalViewMixin. """

    def _make_view(self, query_params, **attrs):
        view = type("_View", (MinimalViewMixin,), attrs)()
        view.request = Mock(query_params=query_params)
        return view

    def test_is_minimal_view_requested(self):
        self.assertTrue(self._make_view({"view": "minimal"}).is_minimal_view_requested())
        self.assertFalse(self._make_view({"view": "full"}).is_minimal_view_requested())
        self.assertFalse(self._make_view({}).is_minimal_view_requested())

    def test_not_requested_returns_data_unchanged(self):
        view = self._make_view({}, minimal_fields=("id",))
        data = [{"id": 1, "heavy": "x"}]
        self.assertIs(view.shape_minimal(data), data)

    def test_requested_projects_each_list_item(self):
        view = self._make_view({"view": "minimal"}, minimal_fields=("id",))
        data = [{"id": 1, "heavy": "x"}, {"id": 2, "heavy": "y"}]
        self.assertEqual(view.shape_minimal(data), [{"id": 1}, {"id": 2}])

    def test_requested_projects_single_object(self):
        view = self._make_view({"view": "minimal"}, minimal_fields=("id",))
        self.assertEqual(view.shape_minimal({"id": 1, "heavy": "x"}), {"id": 1})

    def test_custom_representation_override(self):
        def to_minimal(self, item):  # pylint: disable=unused-argument
            return {"course_id": item["course_details"]["course_id"]}

        view = self._make_view({"view": "minimal"}, to_minimal_representation=to_minimal)
        data = [{"mode": "audit", "course_details": {"course_id": "course-v1:a+b+c", "modes": []}}]
        self.assertEqual(view.shape_minimal(data), [{"course_id": "course-v1:a+b+c"}])

    def test_unconfigured_view_raises_when_minimal_requested(self):
        view = self._make_view({"view": "minimal"})
        with self.assertRaises(ImproperlyConfigured):
            view.shape_minimal([{"id": 1}])

    def test_custom_parameter_name_and_value(self):
        view = self._make_view(
            {"preset": "tiny"},
            minimal_view_query_param="preset",
            minimal_view_value="tiny",
            minimal_fields=("id",),
        )
        self.assertEqual(view.shape_minimal({"id": 1, "heavy": "x"}), {"id": 1})

    def test_explicit_request_argument_wins(self):
        view = self._make_view({}, minimal_fields=("id",))
        other_request = Mock(query_params={"view": "minimal"})
        self.assertEqual(view.shape_minimal({"id": 1, "heavy": "x"}, other_request), {"id": 1})
