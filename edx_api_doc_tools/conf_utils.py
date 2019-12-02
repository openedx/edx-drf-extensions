"""
Functions for setting up API doc generation & viewing in a repository.

External users: import these from __init__.
"""
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.conf.urls import url
from django.views.generic.base import RedirectView
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from .data import ApiInfo


def make_docs_urls(title=None, version=None, email=None, description=None):
    """
    Create views for API documentation and return URL patterns for them.

    If you need more fine-grained control over the views and/or
    the URL configuration, you can use `get_docs_urls`,
    `make_docs_data_view`, `make_docs_ui_view`, and `ApiInfo` manually.

    Arguments:
        * title (str): Title of the APIs ("Open edX APIs")
        * version (str): Version ("v1")
        * email (str): Email address for support ("ocsm@edx.org")
        * description (str): Description of APIs
            "APIs for access to Open edX information"

    Returns: list[RegexURLPattern]
    """
    api_info = ApiInfo(
        title=title, version=version, email=email, description=description
    )
    return get_docs_urls(
        docs_data_view=make_docs_data_view(api_info),
        docs_ui_view=make_docs_ui_view(api_info),
    )


def get_docs_urls(docs_data_view, docs_ui_view):
    """
    Get sane URL patterns to browsable API docs and API docs data.

    Arguments:
        docs_data_view (openapi.Info): View for API docs data.
        docs_ui_view (openapi.Info): View for API docs data.
    """
    return [
        url(
            r'^swagger(?P<format>\.json|\.yaml)$',
            docs_data_view,
            name='apidocs-data',
        ),
        url(
            r'^api-docs/$',
            docs_ui_view,
            name='apidocs-ui',
        ),
        url(
            r'^swagger/$',
            RedirectView.as_view(pattern_name='apidocs-ui', permanent=False),
            name='apidocs-ui-swagger',
        ),
    ]


def make_docs_data_view(api_info):
    """
    Build View for API documentation data (either JSON or YAML).

    Arguments:
        api_info (ApiInfo)

    Returns: View
    """
    return get_schema_view(
        api_info.to_drf_yasg(),
        generator_class=ApiSchemaGenerator,
        public=True,
        permission_classes=(permissions.AllowAny,),
    ).without_ui(cache_timeout=get_docs_cache_timeout())


def make_docs_ui_view(api_info):
    """
    Build View for browsable API documentation.

    Arguments:
        api_info (ApiInfo)

    Returns: View
    """
    return get_schema_view(
        api_info.to_drf_yasg(),
        generator_class=ApiSchemaGenerator,
        public=True,
        permission_classes=(permissions.AllowAny,),
    ).with_ui('swagger', cache_timeout=get_docs_cache_timeout())


class ApiSchemaGenerator(OpenAPISchemaGenerator):
    """
    A schema generator for /api/*

    Only includes endpoints in the /api/* url tree, and sets the path prefix
    appropriately.
    """
    def get_endpoints(self, request):
        endpoints = super(ApiSchemaGenerator, self).get_endpoints(request)
        subpoints = {p: v for p, v in endpoints.items() if p.startswith("/api/")}
        return subpoints

    def determine_path_prefix(self, paths):
        return "/api/"


def get_docs_cache_timeout():
    """
    Return OPENAPI_CACHE_TIMEOUT setting, or zero if it's not defined.
    """
    try:
        return settings.OPENAPI_CACHE_TIMEOUT
    except AttributeError:
        return 0
