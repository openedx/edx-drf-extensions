"""
JWT Authentication cookie utilities.
"""

from django.conf import settings


def jwt_cookie_name():
    return settings.JWT_AUTH.get('JWT_AUTH_COOKIE') or 'edx-jwt-cookie'


def jwt_cookie_header_payload_name():
    return settings.JWT_AUTH.get('JWT_AUTH_COOKIE_HEADER_PAYLOAD') or 'edx-jwt-cookie-header-payload'


def jwt_cookie_signature_name():
    return settings.JWT_AUTH.get('JWT_AUTH_COOKIE_SIGNATURE') or 'edx-jwt-cookie-signature'


def jwt_refresh_cookie_name():
    return settings.JWT_AUTH.get('JWT_AUTH_REFRESH_COOKIE') or 'edx-jwt-refresh-cookie'
