""" Permission classes. """
from rest_framework.permissions import BasePermission
from provider.oauth2.models import AccessToken as DOPAccessToken
from edx_rest_framework_extensions.utils import jwt_decode_handler, is_token_version_incompatable
from openedx.core.djangoapps.oauth_dispatch.utils import is_oauth_scope_enforcement_enabled


class IsSuperuser(BasePermission):
    """ Allows access only to superusers. """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class HasScopedToken(BasePermission):
    """
    The request is authenticated and has the required scopes and organization filters
    """
    def _token_filters(self, decoded_token):
        # get filters list from jwt token and return dict
        if 'filters' in decoded_token:
            filters_list = decoded_token['filters']
            filters = {}
            for each in filters_list:
                each = each.split(':')
                if each[0] in filters.keys():
                    filters[each[0]].append(each[1])
                else:
                    filters[each[0]] = [each[1]]
            return filters

    def has_permission(self, request, view):
        """
        Implement the business logic discussed above
        """
        if is_oauth_scope_enforcement_enabled():
            token = request.auth
            decoded_token = jwt_decode_handler(token)
            # check to see if token is a DOP token
            # if so this represents a client which is implicitly trusted
            # (since it is an internal Open edX application)
            if isinstance(token, DOPAccessToken):
                return True

            if is_token_version_incompatable(decoded_token['version']):
                return False

            if hasattr(view, 'required_scopes'):
                if not getattr(view, 'required_scopes')[0] in decoded_token['scopes']:
                    return False

            has_permission = super(HasScopedToken, self).has_permission(request, view)

            if has_permission:
                setattr(request, 'oauth_scopes_filters', self._token_filters(decoded_token))

            return has_permission
        else:
            return True
