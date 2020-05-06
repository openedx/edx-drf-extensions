"""
Middleware to ensure best practices of DRF and other endpoints.
"""
from django.utils.deprecation import MiddlewareMixin
from edx_django_utils import monitoring
from edx_django_utils.cache import DEFAULT_REQUEST_CACHE

from edx_rest_framework_extensions.auth.jwt.constants import USE_JWT_COOKIE_HEADER
from edx_rest_framework_extensions.auth.jwt.cookies import jwt_cookie_name


class RequestMetricsMiddleware(MiddlewareMixin):
    """
    Adds various request related metrics.

    Possible metrics include:
        request_authenticated_user_set_in_middleware:
            Example values: 'process_request', 'process_view', 'process_response',
            or 'process_exception'. Metric won't exist if user is not authenticated.
        request_auth_type_guess: Example values include: no-user, unauthenticated,
            jwt, bearer, other-token-type, jwt-cookie, or session-or-other
            Note: These are just guesses because if a token was expired, for example,
              the user could have been authenticated by some other means.
        request_client_name: The client name from edx-rest-api-client calls.
        request_referer
        request_user_agent: The user agent string from the request header.
        request_user_id: The user id of the request user.

    This middleware is dependent on the RequestCacheMiddleware. You must
    include this middleware later.  For example::

        MIDDLEWARE = (
            'edx_django_utils.cache.middleware.RequestCacheMiddleware',
            'edx_rest_framework_extensions.middleware.RequestMetricsMiddleware',
        )

    This middleware should also appear after any authentication middleware.

    """
    def process_request(self, request):
        """
        Caches if authenticated user was found.
        """
        self._cache_if_authenticated_user_found_in_middleware(request, 'process_request')

    def process_view(self, request, view_func, view_args, view_kwargs):  # pylint: disable=unused-argument
        """
        Caches if authenticated user was found.
        """
        self._cache_if_authenticated_user_found_in_middleware(request, 'process_view')

    def process_response(self, request, response):
        """
        Add metrics for various details of the request.
        """
        self._cache_if_authenticated_user_found_in_middleware(request, 'process_response')
        self._set_all_request_metrics(request)
        return response

    def process_exception(self, request, exception):  # pylint: disable=unused-argument
        """
        Django middleware handler to process an exception
        """
        self._cache_if_authenticated_user_found_in_middleware(request, 'process_exception')
        self._set_all_request_metrics(request)

    def _set_all_request_metrics(self, request):
        """
        Sets all the request metrics
        """
        self._set_request_auth_type_guess_metric(request)
        self._set_request_user_agent_metrics(request)
        self._set_request_referer_metric(request)
        self._set_request_user_id_metric(request)
        self._set_request_authenticated_user_found_in_middleware_metric()

    def _set_request_user_id_metric(self, request):
        """
        Add request_user_id metric

        Metrics:
             request_user_id
        """
        if hasattr(request, 'user') and hasattr(request.user, 'id') and request.user.id:
            monitoring.set_custom_metric('request_user_id', request.user.id)

    def _set_request_referer_metric(self, request):
        """
        Add metric 'request_referer' for http referer.
        """
        if 'HTTP_REFERER' in request.META and request.META['HTTP_REFERER']:
            monitoring.set_custom_metric('request_referer', request.META['HTTP_REFERER'])

    def _set_request_user_agent_metrics(self, request):
        """
        Add metrics for user agent for python.

        Metrics:
             request_user_agent
             request_client_name: The client name from edx-rest-api-client calls.
        """
        if 'HTTP_USER_AGENT' in request.META and request.META['HTTP_USER_AGENT']:
            user_agent = request.META['HTTP_USER_AGENT']
            monitoring.set_custom_metric('request_user_agent', user_agent)
            if user_agent:
                # Example agent string from edx-rest-api-client:
                #    python-requests/2.9.1 edx-rest-api-client/1.7.2 ecommerce
                #    See https://github.com/edx/edx-rest-api-client/commit/692903c30b157f7a4edabc2f53aae1742db3a019
                user_agent_parts = user_agent.split()
                if len(user_agent_parts) == 3 and user_agent_parts[1].startswith('edx-rest-api-client/'):
                    monitoring.set_custom_metric('request_client_name', user_agent_parts[2])

    def _set_request_auth_type_guess_metric(self, request):
        """
        Add metric 'request_auth_type_guess' for the authentication type used.

        NOTE: This is a best guess at this point.  Possible values include:
            no-user
            unauthenticated
            jwt/bearer/other-token-type
            jwt-cookie
            session-or-other (catch all)

        """
        if not hasattr(request, 'user') or not request.user:
            auth_type = 'no-user'
        elif not request.user.is_authenticated:
            auth_type = 'unauthenticated'
        elif 'HTTP_AUTHORIZATION' in request.META and request.META['HTTP_AUTHORIZATION']:
            token_parts = request.META['HTTP_AUTHORIZATION'].split()
            # Example: "JWT eyJhbGciO..."
            if len(token_parts) == 2:
                auth_type = token_parts[0].lower()  # 'jwt' or 'bearer' (for example)
            else:
                auth_type = 'other-token-type'
        elif USE_JWT_COOKIE_HEADER in request.META and jwt_cookie_name() in request.COOKIES:
            auth_type = 'jwt-cookie'
        else:
            auth_type = 'session-or-other'
        monitoring.set_custom_metric('request_auth_type_guess', auth_type)

    AUTHENTICATED_USER_FOUND_CACHE_KEY = 'edx-drf-extensions.authenticated_user_found_in_middleware'

    def _set_request_authenticated_user_found_in_middleware_metric(self):
        """
        Add metric 'request_authenticated_user_found_in_middleware' if authenticated user was found.
        """
        cached_response = DEFAULT_REQUEST_CACHE.get_cached_response(self.AUTHENTICATED_USER_FOUND_CACHE_KEY)
        if cached_response.is_found:
            monitoring.set_custom_metric(
                'request_authenticated_user_found_in_middleware',
                cached_response.value
            )

    def _cache_if_authenticated_user_found_in_middleware(self, request, value):
        """
        Updates the cached process step in which the authenticated user was found, if it hasn't already been found.
        """
        cached_response = DEFAULT_REQUEST_CACHE.get_cached_response(self.AUTHENTICATED_USER_FOUND_CACHE_KEY)
        if cached_response.is_found:
            # since we are tracking the earliest point the authenticated user was found,
            # and the value was already set in earlier middleware step, do not set again.
            return

        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            DEFAULT_REQUEST_CACHE.set(self.AUTHENTICATED_USER_FOUND_CACHE_KEY, value)
