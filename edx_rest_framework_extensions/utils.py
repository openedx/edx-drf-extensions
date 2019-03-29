""" Utility functions. """

from edx_django_utils.cache import RequestCache
# Note: jwt_decode_handler import is for compatibility with rest_framework_jwt
from edx_rest_framework_extensions.auth.jwt.decoder import jwt_decode_handler  # pylint: disable=unused-import

REQUEST_CACHE = RequestCache('edx_rest_framework_extensions')
