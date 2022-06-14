"""
JWT Authentication cookie utilities.
"""

import logging

from django.conf import settings
from edx_django_utils.monitoring import increment as increment_custom_attribute
from edx_django_utils.monitoring import set_custom_attribute
from rest_framework.request import Request as DrfRequest
from rest_framework.settings import api_settings

from edx_rest_framework_extensions.auth.jwt.authentication import (
    JwtAuthentication,
    get_decoded_jwt_from_auth,
)
from edx_rest_framework_extensions.auth.jwt.decoder import configured_jwt_decode_handler


logger = logging.getLogger(__name__)


def jwt_cookie_name():
    return settings.JWT_AUTH.get('JWT_AUTH_COOKIE') or 'edx-jwt-cookie'


def jwt_cookie_header_payload_name():
    return settings.JWT_AUTH.get('JWT_AUTH_COOKIE_HEADER_PAYLOAD') or 'edx-jwt-cookie-header-payload'


def jwt_cookie_signature_name():
    return settings.JWT_AUTH.get('JWT_AUTH_COOKIE_SIGNATURE') or 'edx-jwt-cookie-signature'


def get_decoded_jwt(request):
    """
    Grab jwt from jwt cookie in request if possible.

    Note: May return the decoded authorization header JWT in some cases.

    Returns a decoded jwt dict if it can be found.
    Returns None if the jwt is not found.
    """
    # use cached jwt if it exists
    decoded_jwt_from_auth = get_decoded_jwt_from_auth(request)
    if decoded_jwt_from_auth:
        return decoded_jwt_from_auth

    # check if jwt cookie exists
    jwt_cookie = request.COOKIES.get(jwt_cookie_name(), None)
    if not jwt_cookie:
        return None

    # Custom attribute can be used to determine priority of caching.
    # Note: Not all IDAs may support increment_custom_attribute
    set_custom_attribute('jwt_cookie_processed', True)
    increment_custom_attribute('jwt_cookie_processed_count')

    # .. toggle_name: DISABLE_NEW_JWT_COOKIE_PROCESSING
    # .. toggle_implementation: DjangoSetting
    # .. toggle_default: False
    # .. toggle_description: Rollout toggle to disable the new Jwt cookie processing code, in case of a bug.
    # .. toggle_use_cases: temporary
    # .. toggle_creation_date: 2022-06-14
    # .. toggle_target_removal_date: 2022-07-01
    # .. toggle_tickets: ARCHBOM-2129
    if getattr(settings, 'DISABLE_NEW_JWT_COOKIE_PROCESSING', False):
        return configured_jwt_decode_handler(jwt_cookie)

    try:
        drf_request = request
        if not isinstance(request, DrfRequest):
            drf_request = DrfRequest(request, parsers=api_settings.DEFAULT_PARSER_CLASSES)
        user_and_auth = JwtAuthentication().authenticate(drf_request)
        if user_and_auth is not None:
            return configured_jwt_decode_handler(user_and_auth[1])

        logger.info('get_decoded_jwt: Failed to decode Jwt cookie.')
    except Exception as ex:  # pylint: disable=broad-except
        logger.info(f'get_decoded_jwt: Unknown error decoding Jwt cookie. {ex!r}')

    return None
