"""
REST API views for reading and writing to the edX Hedgehog Database.

Documented using edx_api_doc_tools.

TODO! finish documenting HedgehogViewSet.

TODO: also give an example of documenting "traditional" (non-ViewSet) DRF views.
"""
from __future__ import absolute_import, unicode_literals

from rest_framework.exceptions import APIException, NotFound
from rest_framework.viewsets import ModelViewSet

from edx_api_doc_tools import path_parameter, query_parameter, schema_for

from .data import get_hedgehogs
from .serializers import HedgehogSerializer


@schema_for(
    'list',
    """
    Fetch the list of edX hedgehogs.

    Hedgehogs can be filtered by minimum weight (grams or ounces),
    their favorite food, whether they graduated college,
    or any combination of those criterion.
    """,
    parameters=[
        query_parameter('min-grams', int, "Filter on whether minimum weight (grams)."),
        query_parameter('min-ounces', float, "Filter hogs by minimum weight (ounces)."),
        query_parameter('fav-food', str, "Filter hogs by favorite food."),
        query_parameter('graduated', bool, "Filter hogs by whether they graudated."),
    ],
)
@schema_for(
    'retrieve',
    # TODO!: The below string becomes the operation's description instead
    #        of its summary for some reason.
    """
    Fetch details for a _single_ hedgehog by key.
    """,
    parameters=[
        path_parameter(
            'hedgehog_key', str, "Key identifying the a hog. Lowercase, letters only."
        ),
    ],
    responses={
        404: 'hedgehog with given key not found',
    },
)
class HedgehogViewSet(ModelViewSet):
    """
    A viewset for hedgehogs.
    """
    serializer_class = HedgehogSerializer
    lookup_field = 'hedgehog_key'

    def get_queryset(self):
        return get_hedgehogs()

    def get_object(self):
        """
        Fetch a specific hedgehog by their key.
        """
        hedgehog_key = self.kwargs[self.lookup_field]
        try:
            hedgehog = next(
                hog for hog in self.get_queryset()
                if hog.key == hedgehog_key
            )
        except StopIteration:
            raise NotFound()
        return hedgehog

    def perform_create(self, serializer):
        """
        Unimplemented: create a Hedeghog; result of a POST.
        """
        raise EndpointNotImplemented()

    def perform_update(self, serializer):
        """
        Unimplemented: create a Hedeghog; result of a PUT.
        """
        raise EndpointNotImplemented()

    def perform_destroy(self, instance):
        """
        Unimplemented: create a Hedeghog; result of a DELETE.
        """
        raise EndpointNotImplemented()


class EndpointNotImplemented(APIException):
    """
    Exception to show that the request to the example view was fine,
    but we haven't implemented it.
    """
    status_code = 501
    default_detail = 'This example endpoint is not implemented.'
    default_code = 'not_implemented'
