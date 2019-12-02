"""
Public Python API for REST documentation.

The functions are split into separate files for code organization,
but they are imported into here so they can be imported
directly from `edx_api_doc_tools`.
"""
from __future__ import absolute_import, unicode_literals

# Expose OpenAPI module through the edx_api_doc_tools package
# so that general users don't have to know about drf_yasg.
from drf_yasg import openapi

# When adding new functions to this API,
# add them to the appropriate sub-module,
# and then "expose" them by importing them here.
# Use explicit imports (as opposed to wildcard imports)
# so that we hide internal names and keep this module
# a nice catalog of functions.
from .conf_utils import (
    ApiSchemaGenerator,
    get_docs_cache_timeout,
    get_docs_urls,
    make_api_info,
    make_docs_data_view,
    make_docs_ui_view,
    make_docs_urls,
)
from .data import (
    FILE_PARAM,
    PARAM_TYPES,
    ParameterLocation,
    parameter,
    path_parameter,
    query_parameter,
    string_parameter,
)
from .view_utils import is_schema_request, schema, schema_for
