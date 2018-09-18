"""
Middleware supporting JWT Authentication.
"""
import logging

from edx_django_utils import monitoring

from edx_rest_framework_extensions.authn.jwt.cookies import (
    jwt_cookie_name,
    jwt_cookie_header_payload_name,
    jwt_cookie_signature_name,
)
from edx_rest_framework_extensions.authn.jwt.constants import JWT_DELIMITER

log = logging.getLogger(__name__)


class JwtAuthCookieMiddleware(object):
    """
    Reconstitutes JWT auth cookies for use by API views which use the JwtAuthentication
    authentication class.

    We split the JWT across two separate cookies in the browser for security reasons. This
    middleware reconstitutes the full JWT into a new cookie on the request object for use
    by the JwtAuthentication class.

    Also, sets the metric 'request_jwt_cookie' with one of the following values:
        'yes': Value when reconstitution is successful.
        'no': Value when both cookies are missing and reconstitution is not possible.
        'missing-XXX': Value when one of the 2 required cookies is missing.  XXX will be
            replaced by the cookie name, which may be set as a setting.  Defaults would
            be 'missing-edx-jwt-cookie-header-payload' or 'missing-edx-jwt-cookie-signature'.

    """

    def _get_missing_cookie_message_and_metric(self, cookie_name):
        """ Returns tuple with missing cookie (log_message, metric_value) """
        cookie_missing_message = '{} cookie is missing. JWT auth cookies will not be reconstituted.'.format(
                cookie_name
        )
        request_jwt_cookie = 'missing-{}'.format(cookie_name)
        return cookie_missing_message, request_jwt_cookie

    def process_request(self, request):
        """
        Reconstitute the full JWT and add a new cookie on the request object.
        """
        header_payload_cookie = request.COOKIES.get(jwt_cookie_header_payload_name())
        signature_cookie = request.COOKIES.get(jwt_cookie_signature_name())

        # Reconstitute JWT auth cookie if split cookies are available.
        if header_payload_cookie and signature_cookie:
            request.COOKIES[jwt_cookie_name()] = '{}{}{}'.format(
                header_payload_cookie,
                JWT_DELIMITER,
                signature_cookie,
            )
            metric_value = 'yes'
        elif header_payload_cookie or signature_cookie:
            # Log unexpected case of only finding one cookie.
            if not header_payload_cookie:
                log_message, metric_value = \
                    self._get_missing_cookie_message_and_metric(jwt_cookie_header_payload_name())
            if not signature_cookie:
                log_message, metric_value = self._get_missing_cookie_message_and_metric(jwt_cookie_signature_name())
            log.warning(log_message)
        else:
            metric_value = 'no'

        monitoring.set_custom_metric('request_jwt_cookie', metric_value)
