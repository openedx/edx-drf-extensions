"""
Static example data for the edX Hedgehog API.
"""
from __future__ import absolute_import, unicode_literals

from collections import namedtuple
from uuid import UUID


Hedgehog = namedtuple(
    'Hedgehog',
    ('uuid', 'key', 'name', 'weight_grams', 'favorite_food', 'is_college_graduate'),
)


def get_hedgehogs():
    """
    Get a list of Hedgehog objects that make up the "edX Hedgehog Database".
    """
    return [
        Hedgehog(_uuid(0), 'spike', 'Spike Lee', 361, 'strawberries', False),
        Hedgehog(_uuid(1), 'skip', 'Skipper Quillson', 410, 'crawlies', False),
        Hedgehog(_uuid(2), 'hedgy', 'Hedgy von Hog', 440, 'critters', False),
        Hedgehog(_uuid(3), 'pepper', 'Pepper Pokes', 380, 'critters', False),
        Hedgehog(_uuid(4), 'hbert', 'Hedgebert the Hedge Fund Manager', 350, 'critters', True),
    ]


def _uuid(i):
    """
    Returns a UUID-4 with a predetermined format, for test repeatability.

    Example:
        ``_uuid(23) == UUID('11111111-2222-4444-8888-000000000023')``
    """
    return UUID('11111111-2222-4444-8888-{:012}'.format(i))
