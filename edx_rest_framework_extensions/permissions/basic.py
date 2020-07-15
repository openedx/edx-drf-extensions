""" Basic Permission classes. """
import logging
from rest_framework.permissions import BasePermission
from edx_rest_framework_extensions.utils import get_username_param


log = logging.getLogger(__name__)


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
        allowed = request.user.username.lower() == get_username_param(request)
        if not allowed:
            log.info(u"Permission IsUserInUrl: not satisfied for requesting user %s.", request.user.username)
        return allowed
