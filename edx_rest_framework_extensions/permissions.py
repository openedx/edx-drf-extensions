""" Permission classes. """
from django.core.exceptions import ImproperlyConfigured
from opaque_keys.edx.keys import CourseKey
from rest_framework.permissions import BasePermission
import waffle

from edx_rest_framework_extensions.authentication import is_jwt_authenticated
from edx_rest_framework_extensions.config import SWITCH_ENFORCE_JWT_SCOPES
from edx_rest_framework_extensions.jwt_decoder import decode_jwt_filters, decode_jwt_scopes


class IsSuperuser(BasePermission):
    """ Allows access only to superusers. """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsStaff(BasePermission):
    """
    Allows access to "global" staff users..
    """
    def has_permission(self, request, view):
        return request.user.is_staff


class IsUserInUrl(BasePermission):
    """
    Allows access if the requesting user matches the user in the URL.
    """
    def has_permission(self, request, view):
        user_parameter_name = 'username'
        url_username = (
            request.GET.get(user_parameter_name, '') or
            getattr(request, 'parser_context', {}).get('kwargs', {}).get(user_parameter_name, '')
        )
        return request.user.username.lower() == url_username.lower()


class IsJwtAuthenticated(BasePermission):
    """
    Returns whether the request was successfully authenticated with JwtAuthentication.
    """
    def has_permission(self, request, view):
        return is_jwt_authenticated(request)


class JwtHasScope(BasePermission):
    """
    The request is authenticated as a user and the token used has the right scope.
    """
    message = 'JWT missing required scopes.'

    def has_permission(self, request, view):
        if _should_skip_jwt_scope_enforcement(request):
            return True
        jwt_scopes = decode_jwt_scopes(request.auth)
        required_scopes = set(self.get_scopes(request, view))
        if required_scopes.issubset(jwt_scopes):
            return True
        return False

    def get_scopes(self, request, view):
        """
        Return the required scopes defined on the view.
        """
        try:
            return getattr(view, 'required_scopes')
        except AttributeError:
            raise ImproperlyConfigured('JwtHasScope requires the view to define the required_scopes attribute')


class JwtHasContentOrgFilterForRequestedCourse(BasePermission):
    """
    The JWT used to authenticate contains the appropriate content provider
    filter for the requested course resource.
    """
    message = 'JWT missing required content_org filter.'

    def has_permission(self, request, view):
        """
        Ensure that the course_id kwarg provided to the view contains one
        of the organizations specified in the content provider filters
        in the JWT used to authenticate.
        """
        if _should_skip_jwt_scope_enforcement(request):
            return True
        course_key = CourseKey.from_string(view.kwargs.get('course_id'))
        jwt_filters = decode_jwt_filters(request.auth)
        for provider_type, filter_value in jwt_filters:
            if provider_type == 'content_org' and filter_value == course_key.org:
                return True
        return False


def _should_skip_jwt_scope_enforcement(request):
    """
    Returns True if either the request is not JWT authenticated or if
    JWT scopes enforcement is disabled.
    """
    if not is_jwt_authenticated(request):
        return True
    return not waffle.switch_is_active(SWITCH_ENFORCE_JWT_SCOPES)
