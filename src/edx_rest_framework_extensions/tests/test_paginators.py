""" Tests paginator methods """

from collections import namedtuple
from unittest import TestCase
from unittest.mock import MagicMock, Mock

import ddt
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.test import RequestFactory
from rest_framework import serializers

from edx_rest_framework_extensions.paginators import (
    IterablePaginationMixin,
    NamespacedPageNumberPagination,
    paginate_manually,
    paginate_search_results,
)


@ddt.ddt
class PaginateSearchResultsTestCase(TestCase):
    """Test cases for paginate_search_results method"""

    def setUp(self):
        super().setUp()

        self.default_size = 6
        self.default_page = 1
        self.search_results = {
            "count": 3,
            "took": 1,
            "results": [
                {
                    '_id': 0,
                    'data': {
                        'pk': 0,
                        'name': 'object 0'
                    }
                },
                {
                    '_id': 1,
                    'data': {
                        'pk': 1,
                        'name': 'object 1'
                    }
                },
                {
                    '_id': 2,
                    'data': {
                        'pk': 2,
                        'name': 'object 2'
                    }
                },
                {
                    '_id': 3,
                    'data': {
                        'pk': 3,
                        'name': 'object 3'
                    }
                },
                {
                    '_id': 4,
                    'data': {
                        'pk': 4,
                        'name': 'object 4'
                    }
                },
                {
                    '_id': 5,
                    'data': {
                        'pk': 5,
                        'name': 'object 5'
                    }
                },
            ]
        }
        self.mock_model = Mock()
        self.mock_model.objects = Mock()
        self.mock_model.objects.filter = Mock()

    @ddt.data(
        (1, 1, True),
        (1, 3, True),
        (1, 5, True),
        (1, 10, False),
        (2, 1, True),
        (2, 3, False),
        (2, 5, False),
    )
    @ddt.unpack
    def test_paginated_results(self, page_number, page_size, has_next):
        """ Test the page returned has the expected db objects and acts
        like a proper page object.
        """
        id_range = get_object_range(page_number, page_size)
        db_objects = [build_mock_object(obj_id) for obj_id in id_range]
        self.mock_model.objects.filter = MagicMock(return_value=db_objects)

        page = paginate_search_results(self.mock_model, self.search_results, page_size, page_number)

        self.mock_model.objects.filter.assert_called_with(pk__in=id_range)
        self.assertEqual(db_objects, page.object_list)
        self.assertTrue(page.number, page_number)
        self.assertEqual(page.has_next(), has_next)

    def test_paginated_results_last_keyword(self):
        """ Test the page returned has the expected db objects and acts
        like a proper page object using 'last' keyword.
        """
        page_number = 2
        page_size = 3
        id_range = get_object_range(page_number, page_size)
        db_objects = [build_mock_object(obj_id) for obj_id in id_range]
        self.mock_model.objects.filter = MagicMock(return_value=db_objects)
        page = paginate_search_results(self.mock_model, self.search_results, page_size, 'last')

        self.mock_model.objects.filter.assert_called_with(pk__in=id_range)
        self.assertEqual(db_objects, page.object_list)
        self.assertTrue(page.number, page_number)
        self.assertFalse(page.has_next())

    @ddt.data(10, -1, 0, 'str')
    def test_invalid_page_number(self, page_num):
        """ Test that a Http404 error is raised with non-integer and out-of-range pages
        """
        with self.assertRaises(Http404):
            paginate_search_results(self.mock_model, self.search_results, self.default_size, page_num)


class NamespacedPaginationTestCase(TestCase):
    """
    Test behavior of `NamespacedPageNumberPagination`
    """

    TestUser = namedtuple('TestUser', ['username', 'email'])

    class TestUserSerializer(serializers.Serializer):  # pylint: disable=abstract-method
        """
        Simple serializer to paginate results from
        """
        username = serializers.CharField()
        email = serializers.CharField()

    expected_data = {
        'results': [
            {'username': 'user_5', 'email': 'user_5@example.com'},
            {'username': 'user_6', 'email': 'user_6@example.com'},
            {'username': 'user_7', 'email': 'user_7@example.com'},
            {'username': 'user_8', 'email': 'user_8@example.com'},
            {'username': 'user_9', 'email': 'user_9@example.com'},
        ],
        'pagination': {
            'next': 'http://testserver/endpoint?page=3&page_size=5',
            'previous': 'http://testserver/endpoint?page_size=5',
            'count': 25,
            'num_pages': 5,
        }
    }

    def setUp(self):
        super().setUp()
        self.paginator = NamespacedPageNumberPagination()
        self.users = [self.TestUser(f'user_{idx}', f'user_{idx}@example.com') for idx in range(25)]
        self.request_factory = RequestFactory()

    def test_basic_pagination(self):
        request = self.request_factory.get('/endpoint', data={'page': 2, 'page_size': 5})
        request.query_params = {'page': 2, 'page_size': 5}
        paged_users = self.paginator.paginate_queryset(self.users, request)
        results = self.TestUserSerializer(paged_users, many=True).data
        self.assertEqual(self.expected_data, self.paginator.get_paginated_response(results).data)


def build_mock_object(obj_id):
    """ Build a mock object with the passed id"""
    mock_object = Mock()
    object_config = {
        'pk': obj_id,
        'name': f"object {obj_id}"
    }
    mock_object.configure_mock(**object_config)
    return mock_object


def get_object_range(page, page_size):
    """ Get the range of expected object ids given a page and page size.
    This will take into account the max_id of the sample data.  Currently 5.
    """
    max_id = 5
    start = min((page - 1) * page_size, max_id)
    end = min(start + page_size, max_id + 1)
    return list(range(start, end))


class ManualPaginationTestCase(TestCase):
    """ Test cases for paginate_manually() and IterablePaginationMixin. """

    def setUp(self):
        super().setUp()
        self.items = [{'id': idx} for idx in range(25)]
        self.request_factory = RequestFactory()

    def _request(self, **params):
        request = self.request_factory.get('/endpoint', data=params)
        request.query_params = params
        return request

    def test_paginate_manually_default_pagination(self):
        request = self._request(page=2, page_size=5)
        response = paginate_manually(request, self.items, serialize=lambda page: page)

        self.assertEqual(response.data['results'], self.items[5:10])
        self.assertEqual(response.data['count'], 25)
        self.assertEqual(response.data['num_pages'], 5)
        self.assertEqual(response.data['current_page'], 2)
        self.assertEqual(response.data['start'], 5)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)

    def test_paginate_manually_serialize_receives_only_the_page(self):
        request = self._request(page=1, page_size=3)
        seen = []
        paginate_manually(request, self.items, serialize=lambda page: seen.append(list(page)))
        self.assertEqual(seen, [self.items[:3]])

    def test_paginate_manually_custom_pagination_class(self):
        request = self._request(page=1, page_size=4)
        response = paginate_manually(
            request, self.items, serialize=lambda page: page,
            pagination_class=NamespacedPageNumberPagination,
        )
        self.assertEqual(response.data['results'], self.items[:4])
        self.assertEqual(response.data['pagination']['count'], 25)

    def test_mixin_uses_get_serializer(self):
        items = self.items

        class _FakeSerializer:
            """ Stand-in for a DRF serializer: uppercases nothing, wraps items. """
            def __init__(self, page, many=False):
                assert many
                self.data = [{'wrapped': item['id']} for item in page]

        class _View(IterablePaginationMixin):
            def get_serializer(self, page, many=False):
                return _FakeSerializer(page, many=many)

        response = _View().paginate_iterable(self._request(page=1, page_size=2), items)
        self.assertEqual(response.data['results'], [{'wrapped': 0}, {'wrapped': 1}])
        self.assertEqual(response.data['count'], 25)

    def test_mixin_explicit_serialize_argument(self):
        class _View(IterablePaginationMixin):
            pass

        response = _View().paginate_iterable(
            self._request(page=1, page_size=2), self.items, serialize=list,
        )
        self.assertEqual(response.data['results'], self.items[:2])

    def test_mixin_without_serializer_or_serialize_raises(self):
        class _View(IterablePaginationMixin):
            pass

        with self.assertRaises(ImproperlyConfigured):
            _View().paginate_iterable(self._request(page=1), self.items)

    def test_mixin_with_none_pagination_class_raises(self):
        class _View(IterablePaginationMixin):
            pagination_class = None

        with self.assertRaises(ImproperlyConfigured):
            _View().paginate_iterable(self._request(page=1), self.items, serialize=list)
