"""
REST API serializers for reading and writing to the edX Hedgehog Database.
"""
from __future__ import absolute_import, unicode_literals

from rest_framework import serializers


# pylint: disable=abstract-method


class HedgehogSerializer(serializers.Serializer):
    """
    Serializer for a hedgehog.
    """
    uuid = serializers.UUIDField()
    key = serializers.SlugField()
    name = serializers.CharField()
    weight_grams = serializers.IntegerField()
    # TODO: How can we make `weight_ounces` be schema'd as a float instead of a string?
    weight_ounces = serializers.SerializerMethodField()
    fav_food = serializers.ChoiceField(
        [
            ('critters', 'Critters'),
            ('crawlies', 'Crawly things'),
            ('strawberries', 'Strawberries'),
        ],
        allow_blank=True,
        source='favorite_food',
    )
    is_college_graduate = serializers.BooleanField(default=False)

    def get_weight_ounces(self, obj):
        """
        Convert the weight of the hedgehog `obj` from an `int` number of grams
        to a `float` number of ounces.
        """
        return obj.weight_grams * 28.3495
