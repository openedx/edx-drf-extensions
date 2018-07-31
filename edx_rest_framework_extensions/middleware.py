"""
Middleware to ensure best practices of DRF endpoints.
"""
import logging

from edx_django_utils import monitoring
from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication

from .permissions import NotJwtRestrictedApplication

log = logging.getLogger(__name__)


class EnsureJWTAuthSettingsMiddleware(object):
    """
    Django middleware object that ensures the proper Permission classes
    are set on all endpoints that use JWTAuthentication.
    """
    _required_permission_classes = (NotJwtRestrictedApplication,)

    def _includes_base_class(self, iter_classes, base_class):
        """
        Returns whether any class in iter_class is a subclass of the given base_class.
        """
        return any(
            issubclass(auth_class, base_class) for auth_class in iter_classes,
        )

    def _add_missing_jwt_permission_classes(self, view_class):
        """
        Adds permissions classes that should exist for Jwt based authentication,
        if needed.
        """
        view_permissions = list(getattr(view_class, 'permission_classes', []))

        # Not all permissions are classes, some will be ConditionalPermission
        # objects from the rest_condition library. So we have to crawl all those
        # and expand them to see if our target classes are inside the
        # conditionals somewhere.
        permission_classes = []
        classes_to_add = []
        while view_permissions:
            permission = view_permissions.pop()
            if not hasattr(permission, 'perms_or_conds'):
                permission_classes.append(permission)
            else:
                for child in getattr(permission, 'perms_or_conds', []):
                    view_permissions.append(child)

        for perm_class in self._required_permission_classes:
            if not self._includes_base_class(permission_classes, perm_class):
                log.warning(
                    u"The view %s allows Jwt Authentication but needs to include the %s permission class (adding it for you)",
                    view_class.__name__,
                    perm_class.__name__,
                )
                classes_to_add.append(perm_class)

        if classes_to_add:
            view_class.permission_classes += tuple(classes_to_add)

    def process_view(self, request, view_func, view_args, view_kwargs):  # pylint: disable=unused-argument
        # Views as functions store the view's class in the 'view_class' attribute.
        # Viewsets store the view's class in the 'cls' attribute.
        view_class = getattr(
            view_func,
            'view_class',
            getattr(view_func, 'cls', view_func),
        )

        view_authentication_classes = getattr(view_class, 'authentication_classes', tuple())
        if self._includes_base_class(view_authentication_classes, BaseJSONWebTokenAuthentication):
            self._add_missing_jwt_permission_classes(view_class)


class RequestMetricsMiddleware(object):
    """
    Adds various request related metrics.
    """

    def process_response(self, request, response):
        """
        Add metrics for various details of the request.
        """
        self._set_request_auth_type_metric(request)
        self._set_request_user_agent_metrics(request)
        self._set_request_referer_metric(request)

        return response

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

    def _set_request_auth_type_metric(self, request):
        """
        Add metric 'request_auth_type' for the authentication type used.

        NOTE: This is a best guess at this point.  Possible values include:
            no-user
            unauthenticated
            jwt/bearer/other-token-type
            session-or-unknown (catch all)

        """
        if 'HTTP_AUTHORIZATION' in request.META and request.META['HTTP_AUTHORIZATION']:
            token_parts = request.META['HTTP_AUTHORIZATION'].split()
            # Example: "JWT eyJhbGciO..."
            if len(token_parts) == 2:
                auth_type = token_parts[0].lower()  # 'jwt' or 'bearer' (for example)
            else:
                auth_type = 'other-token-type'
        elif not hasattr(request, 'user') or not request.user:
            auth_type = 'no-user'
        elif not request.user.is_authenticated():
            auth_type = 'unauthenticated'
        else:
            auth_type = 'session-or-unknown'
        monitoring.set_custom_metric('request_auth_type', auth_type)
