"""
TODO
"""
from __future__ import absolute_import, unicode_literals

from rest_framework import serializers


# pylint: disable=abstract-method


class HedgehogSerializer(serializers.Serializer):
    """
    TODO
    """
    uuid = serializers.UUIDField()
    key = serializers.SlugField()
    name = serializers.CharField()
    weight_grams = serializers.IntegerField()
    weight_ounces = serializers.SerializerMethodField()  # TODO: how to make float??
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
        TODO
        """
        return obj.weight_grams * 28.3495
