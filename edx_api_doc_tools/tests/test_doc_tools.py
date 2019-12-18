"""
Tests for API docs tooling.
"""
from __future__ import absolute_import, unicode_literals

import json
from os.path import dirname, join

from django.test import SimpleTestCase
from django.test.utils import override_settings

from ..example import urls as example_urls


@override_settings(ROOT_URLCONF=example_urls.__name__)
class DocViewTests(SimpleTestCase):
    """
    Test that the API docs generated from the example Hedgehog API look right.
    """
    base_path = dirname(__file__)
    path_of_expected_schema = join(base_path, 'expected_schema.json')
    path_of_actual_schema = join(base_path, 'actual_schema.json')

    def test_get_data_view(self):
        """
        Test that the generated API schema equals the reference schema.

        How this test works:
        * Generate a Swagger schema by GETting /swagger.json, and then dumping it to
          actual_schema.json.
        * Load example_schema.json.
        * Assert that actual_schema.json and example_schema.json are equivalent.

        If you make a change to the doc tools or the example API that change the
        generated schema, here's how to update this test:
        * Run the test, which should fail with an AssertionError about the
          generated schema.
        * Copy the contents of actual_schema.json into https://editor.swagger.io
        * Make sure the browsable API looks correct,
          and make sure the contents of the schema file look sane.
        * If everything looks right, copy actual_schema.json into expected_schema.json
          and commit the change, making it the new reference schema.
        """
        response = self.client.get('/swagger.json')
        assert response.status_code == 200
        actual_schema = response.json()
        with open(self.path_of_actual_schema, 'w') as f:
            json.dump(actual_schema, f, indent=4)
        with open(self.path_of_expected_schema, 'r') as schema_file:
            expected_schema = json.load(schema_file)
        assert actual_schema == expected_schema, (
            "Generated schema (dumped to actual_schema.json) "
            "did not match schema loaded from expected_schema.json."
        )

    def test_get_ui_view(self):
        """
        Test that the UI view returns a page with the expected title.

        We can't assert anything about page content, because that is all loaded
        via an AJAX call to /api-docs/?format=openapi
        """
        response = self.client.get('/api-docs/')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert '<title>edX Hedgehog Service API</title>' in content

    def test_ui_data_endpoint(self):
        """
        Test that the the endpoint that the UI calls via AJAX returns the same data
        as the schema endpoint.
        """
        data_response = self.client.get('/swagger.json', )
        ui_data_response = self.client.get('/api-docs/?format=openapi')
        assert ui_data_response.status_code == data_response.status_code == 200
        expected = data_response.json()
        # Cannot use `.json()` because response has content type 'application/openapi+json'.
        actual = json.loads(ui_data_response.content.decode('utf-8'))
        assert actual == expected
