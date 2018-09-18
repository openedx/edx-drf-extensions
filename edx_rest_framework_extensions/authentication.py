"""
Deprecated imports for authentication classes that moved.

TODO: ARCH-244: Remove this file of backward compatible imports.
"""
from edx_rest_framework_extensions.auth.jwt.authentication import (
    JwtAuthentication,
    is_jwt_authenticated,
)  # pylint: disable=unused-import
from edx_rest_framework_extensions.auth.bearer.authentication import (
    BearerAuthentication,
)  # pylint: disable=unused-import
