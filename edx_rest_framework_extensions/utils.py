""" Utility functions. """

# for compatibility with rest_framework_jwt
# pylint: disable=unused-import
from edx_rest_framework_extensions.auth.jwt.decoder import jwt_decode_handler


def get_username_param(request):
    user_parameter_name = 'username'
    url_username = (
        getattr(request, 'parser_context', {}).get('kwargs', {}).get(user_parameter_name, '') or
        request.GET.get(user_parameter_name, '')
    )
    return url_username.lower()
