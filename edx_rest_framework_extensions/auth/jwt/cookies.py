"""
JWT Authentication cookie utilities.
"""

from django.conf import settings


def jwt_cookie_name():
    """
    Returns the JWT cookie name from either the JWT_AUTH setting, or the
    default if the setting is not set.
    """
    value = settings.JWT_AUTH.get('JWT_AUTH_COOKIE')
    if value:
        return value

    return 'edx-jwt-cookie'


def jwt_cookie_header_payload_name():
    """
    Returns the JWT cookie header payload name from either the JWT_AUTH
    setting, or the default if the setting is not set.
    """
    value = settings.JWT_AUTH.get('JWT_AUTH_COOKIE_HEADER_PAYLOAD')
    if value:
        return value

    return 'edx-jwt-cookie-header-payload'


def jwt_cookie_signature_name():
    """
    Returns the JWT cookie signature name from either the JWT_AUTH
    setting, or the default if the setting is not set.
    """
    value = settings.JWT_AUTH.get('JWT_AUTH_COOKIE_SIGNATURE')
    if value:
        return value

    return 'edx-jwt-cookie-signature'
