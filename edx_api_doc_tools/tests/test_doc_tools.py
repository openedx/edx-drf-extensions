"""
Tests for API docs tooling.
"""
from __future__ import absolute_import, unicode_literals

import json
from os.path import dirname, join

import ddt
from django.test import SimpleTestCase
from django.test.utils import override_settings
from drf_yasg import openapi

from .. import ApiInfo, Param, ParamLocation
from ..example import urls as example_urls


@ddt.ddt
class DataTests(SimpleTestCase):
    """
    Tests of our data structures and their ability to be converted to those
    of drf-yasg.
    """
    def test_default_api_to_drf_yasg(self):
        """
        An ApiInfo instance with default values can be converted to drf-yasg form.
        """
        default_api_info = ApiInfo()
        yasg_info = default_api_info.to_drf_yasg()
        assert yasg_info.title == "Open edX APIs"
        assert yasg_info.contact.email == "oscm@edx.org"
        assert yasg_info.description == "APIs for access to Open edX information"

    good_param_kwargs = {
        'name': 'testparam',
        'location': ParamLocation.PATH,
        'param_type': int,
        'description': "I am a test parameter",
    }

    def test_param_to_drf_yasg(self):
        """
        An Param instance can be converted to drf-yasg form.
        """
        param = Param(**self.good_param_kwargs)
        yasg_param = param.to_drf_yasg()
        assert yasg_param.name == 'testparam'
        assert yasg_param.in_ == openapi.IN_PATH
        assert yasg_param.type == openapi.TYPE_INTEGER
        assert yasg_param.description == "I am a test parameter"

    @ddt.data(
        ('name', None, "name .* is not of type"),
        ('location', 'BODY', "ParamLocation"),
        ('param_type', dict, "PARAM_TYPES"),
        ('description', 5, "description .* is not of type"),
    )
    @ddt.unpack
    def test_value_errors(self, bad_kwarg_name, bad_kwarg_value, error_regex):
        """
        Param() raises the correct ValueErrors given different bad values.
        """
        param_kwargs = self.good_param_kwargs.copy()
        param_kwargs[bad_kwarg_name] = bad_kwarg_value
        # assertRaisesRegex isn't deprecated; this is a Pylint issue.
        with self.assertRaisesRegex(  # pylint: disable=deprecated-method
            ValueError, error_regex
        ):
            Param(**param_kwargs)


@override_settings(ROOT_URLCONF=example_urls.__name__)
class DocViewTests(SimpleTestCase):
    """
    TODO talk about expected_schema.json, mention https://editor.swagger.io/
    """
    base_path = dirname(__file__)
    path_of_expected_schema = join(base_path, 'expected_schema.json')
    path_of_actual_schema = join(base_path, 'actual_schema.json')

    @classmethod
    def setUpClass(cls):
        super(DocViewTests, cls).setUpClass()
        with open(cls.path_of_expected_schema, 'r') as schema_file:
            # pylint: disable=attribute-defined-outside-init
            cls.expected_schema = json.load(schema_file)

    def test_get_ui_view(self):
        """
        TODO
        """
        response = self.client.get('/api-docs/')
        assert response.status_code == 200

    def test_get_data_view(self):
        """
        TODO
        """
        response = self.client.get('/swagger.json')
        assert response.status_code == 200
        actual_schema = response.json()
        with open(self.path_of_actual_schema, 'w') as f:
            json.dump(actual_schema, f, indent=4)
        assert actual_schema == self.expected_schema, (
            "Generated schema (dumped to actual_schema.json) "
            "did not match schema loaded from expected_schema.json."
        )
