"""
Utilities for annotating API views with schema info as well as
extracting schema info from them.

External users: import these from __init__.
"""
from __future__ import absolute_import, unicode_literals

import six
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema

from .internal_utils import dedent


def schema_for(method_name, docstring, *schema_args, **schema_kwargs):
    """
    Decorate a class to specify a schema for one of its methods.

    Useful when the method you are describing is not defined inside of your
    class body, but is instead defined somewhere up in the DRF view hierarchy.
    (For applying a schema directly to a method, use `schema`).

    Valid values of `method_name` include:
        'list',
        'get', 'GET', 'retrieve',
        'post', 'POST', 'create',
        'put', 'PUT',
        'patch', 'PATCH', 'update',
        'delete', 'DELETE', and 'destroy'.

    The docstring of the specified method is replaced with `docstring`.
    """
    def schema_for_inner(view_class):
        """
        Final view class decorator
        """
        decorated_class = method_decorator(
            name=method_name,
            decorator=schema(*schema_args, **schema_kwargs),
        )(view_class)
        view_func = six.get_unbound_function(getattr(decorated_class, method_name))
        view_func.__doc__ = docstring
        return decorated_class
    return schema_for_inner


def schema(*parameters):
    """
    Decorator for documenting an API endpoint.

    The operation summary and description are taken from the function docstring. All
    description fields should be in Markdown and will be automatically dedented.

    Args:
        parameters (list[Param]): Parameters to the API endpoint.
    """
    yasg_parameters = [param.to_drf_yasg() for param in parameters]

    def schema_inner(view_func):
        """
        Final view method decorator
        """
        summary = None
        description = None
        if view_func.__doc__:
            doc_lines = view_func.__doc__.strip().split("\n")
            if doc_lines:
                summary = doc_lines[0].strip()
            if len(doc_lines) > 1:
                description = dedent("\n".join(doc_lines[1:]))
        return swagger_auto_schema(
            manual_parameters=yasg_parameters,
            operation_summary=summary,
            operation_description=description,
        )(view_func)
    return schema_inner


def is_schema_request(request):
    """
    Is this request serving an OpenAPI schema?
    """
    return request.query_params.get('format') == 'openapi'
