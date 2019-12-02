"""
Data definitions for API schemas.

These are generally thin wrappers around drf-yasg's
OpenAPI schema types. We wrap them so that we can
easily switch from drf-yasg to another supporting
library if we must without affecting clients of this
library.
"""
from __future__ import absolute_import, unicode_literals

from enum import Enum

import six
from drf_yasg import openapi

from .internal_utils import dedent


class ApiInfo(object):
    """
    High-level information about an API.
    """
    def __init__(
            self,
            title="Open edX APIs",
            version="v1",
            email="oscm@edx.org",
            description="APIs for access to Open edX information",
    ):
        self.title = title
        self.version = version
        self.email = email
        self.description = description

    def to_drf_yasg(self):
        """
        Convert this object to its drf-yasg-compatible representation.
        """
        return openapi.Info(
            title=self.title,
            default_version=self.version,
            contact=openapi.Contact(email=self.email or "ocsm@edx.org"),
            description=self.description,
        )


class Param(object):
    """
    Documentation for a parameter to an API endpoint.
    """
    def __init__(self, name, location, param_type, description=None):
        """
        Initialize a Param, validating argument types.

        Arguments:
            name (str)
            location (ParamLocation)
            param_type (object): a member of `PARAM_TYPES`
            description (str): optional
        """
        if not isinstance(name, six.text_type):
            raise ValueError(
                "name {!r} is not of type {}".format(name, six.text_type)
            )
        if not isinstance(location, ParamLocation):
            raise ValueError(
                "{!r} is not a ParamLocation".format(location)
            )
        if param_type not in PARAM_TYPES:
            raise ValueError(
                "{!r} is not in PARAM_TYPES".format(param_type)
            )
        if not isinstance(description, (type(None), six.text_type)):
            raise ValueError(
                "description {!r} is not of type {}".format(description, six.text_type)
            )
        self.name = name
        self.location = location
        self.param_type = param_type
        self.description = description

    @property
    def dedented_description(self):
        """
        Returns dedented description of parameter.
        """
        return dedent(self.description) if self.description else None

    def to_drf_yasg(self):
        """
        Convert this object to its drf-yasg-compatible representation.
        """
        return openapi.Parameter(
            self.name,
            self.location.to_drf_yasg(),
            type=param_type_to_drf_yasg_type(self.param_type),
            description=self.dedented_description,
        )


_PARAM_TYPES_TO_DRF_YASG = {
    object: openapi.TYPE_OBJECT,
    str: openapi.TYPE_STRING,
    float: openapi.TYPE_NUMBER,
    int: openapi.TYPE_INTEGER,
    bool: openapi.TYPE_BOOLEAN,
    list: openapi.TYPE_ARRAY,
    'file': openapi.TYPE_FILE,
}
PARAM_TYPES = frozenset(_PARAM_TYPES_TO_DRF_YASG.keys())


def param_type_to_drf_yasg_type(param_type):
    """
    Convert a PARAM_TYPE to a drf_yasg.openapi.TYPE_ constant.
    """
    try:
        return _PARAM_TYPES_TO_DRF_YASG[param_type]
    except KeyError:
        raise ValueError(
            "{!r} is not in PARAM_TYPES".format(param_type)
        )


class ParamLocation(Enum):
    """
    Location of API parameter in request.
    """
    BODY = openapi.IN_BODY
    PATH = openapi.IN_PATH
    QUERY = openapi.IN_QUERY
    FORM = openapi.IN_FORM
    HEADER = openapi.IN_HEADER

    def to_drf_yasg(self):
        """
        Convert this object to its drf-yasg-compatible representation.
        """
        return self.value
