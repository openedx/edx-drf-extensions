"""
Deprecated imports for jwt_decoder code that moved.

TODO: ARCH-244: Remove this file of backward compatible imports.
"""
from edx_rest_framework_extensions.auth.jwt.decoder import (
    JwtTokenVersion,
    decode_jwt_filters,
    decode_jwt_is_restricted,
    decode_jwt_scopes,
    jwt_decode_handler,
)  # pylint: disable=unused-import
