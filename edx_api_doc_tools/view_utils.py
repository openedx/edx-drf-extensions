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
    (For applying a schema directly to a method, use the `schema` decorator).

    DRF method names include:
        'list', 'retrieve', 'get',
        'post', 'create',
        'put', 'update',
        'patch', 'partial_update',
        'delete', and 'destroy'.

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


def schema(parameters=None, responses=None):
    """
    Decorator for documenting an API endpoint.

    The operation summary and description are taken from the function docstring. All
    description fields should be in Markdown and will be automatically dedented.

    Args:
        parameters (list[openapi.Parameter]):
            Optional list of parameters to the API endpoint.
        responses (dict[int, object]):
            Optional map from HTTP statuses to either:
                * a serializer class corresponding to that status
                * a string describing when that status occurs
                * an openapi.Schema object
                * `None`, which indicates "don't include this response".
    """
    for param in parameters or ():
        param.description = dedent(param.description)

    # TODO: Remove this line when we drop Python 2 support.
    responses = _fix_responses_for_python_2(responses)

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
            manual_parameters=parameters,
            responses=responses,
            operation_summary=summary,
            operation_description=description,
        )(view_func)
    return schema_inner


def _fix_responses_for_python_2(responses):
    """
    This is a temporary hack, necessary because drf-yasg doesn't explicitly support Python 2.

    Specifically, drf-yasg expects string response descriptions to be of type `str`,
    which in Py2, doesn't work on unicode strings.

    The offending line:
    https://github.com/axnsan12/drf-yasg/blob/13311582ea67da80204176211319b0a715802568/src/drf_yasg/inspectors/view.py#L249

    TODO: Remove this function when we drop Python 2 support.

    Arguments:
        responses: dict[int, object]

    Returns: dict[int, object]
    """
    if six.PY3 or responses is None:
        return responses
    return {
        http_status: (
            value.encode('utf-8')
            if isinstance(value, unicode)  # pylint: disable=undefined-variable
            else value
        )
        for http_status, value in responses.iteritems()
    }


def is_schema_request(request):
    """
    Is this request serving an OpenAPI schema?
    """
    return request.query_params.get('format') == 'openapi'
