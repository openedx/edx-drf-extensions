"""
TODO
"""
from __future__ import absolute_import, unicode_literals

from rest_framework.exceptions import APIException, NotFound
from rest_framework.viewsets import ModelViewSet

from .. import Param
from .. import ParamLocation as Loc
from .. import schema_for
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
    Param('min-grams', Loc.QUERY, int, "Filter on whether minimum weight (grams)."),
    Param('min-ounces', Loc.QUERY, float, "Filter hogs by minimum weight (ounces)."),
    Param('fav-food', Loc.QUERY, str, "Filter hogs by favorite food."),
    Param('graduated', Loc.QUERY, bool, "Filter hogs by whether they graudated."),
)
@schema_for(
    'retrieve',
    """
    Fetch details for a _single_ hedgehog by key.
    """,
    Param('hedgehog_key', Loc.PATH, str, "Key identifying the a hog. Lowercase, letters only."),
)
@schema_for(
    'create',
    """
    """
)
class HedgehogViewSet(ModelViewSet):
    """
    TODO this is the hedgehog viewset
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
        TODO
        """
        raise EndpointNotImplemented()

    def perform_update(self, serializer):
        """
        TODO
        """
        raise EndpointNotImplemented()

    def perform_destroy(self, instance):
        """
        TODO
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
