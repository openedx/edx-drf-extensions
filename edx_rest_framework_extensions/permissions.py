""" Permission classes. """
from django.core.exceptions import ImproperlyConfigured
from opaque_keys.edx.keys import CourseKey
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from edx_rest_framework_extensions.decorators import (
    skip_unless_jwt_authenticated,
    skip_unless_jwt_scopes_enforced,
)
from edx_rest_framework_extensions.utils import decode_jwt_filters, decode_jwt_scopes


class IsSuperuser(BasePermission):
    """ Allows access only to superusers. """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class JwtHasScope(BasePermission):
    """
    The request is authenticated as a user and the token used has the right scope.
    """
    message = 'JWT missing required scopes.'

    @skip_unless_jwt_scopes_enforced
    @skip_unless_jwt_authenticated
    def has_permission(self, request, view):
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

    @skip_unless_jwt_scopes_enforced
    @skip_unless_jwt_authenticated
    def has_permission(self, request, view):
        """
        Ensure that the course_id kwarg provided to the view contains one
        of the organizations specified in the content provider filters
        in the JWT used to authenticate.
        """
        course_key = CourseKey.from_string(view.kwargs.get('course_id'))
        jwt_filters = decode_jwt_filters(request.auth)
        for provider_type, filter_value in jwt_filters:
            if provider_type == 'content_org' and filter_value == course_key.org:
                return True
        return False
