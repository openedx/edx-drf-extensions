"""
Permission classes related to redirect functionality required by JwtRedirectToLoginIfUnauthenticatedMiddleware.
"""
from rest_framework.permissions import BasePermission, IsAuthenticated


class LoginRedirectIfUnauthenticated(IsAuthenticated):
    """
    A DRF permission class that will login redirect unauthorized users.

    It can be used to convert a plain Django view that was using @login_required
    into a DRF APIView, which is useful to enable our DRF JwtAuthentication class.

    Requires JwtRedirectToLoginIfUnauthenticatedMiddleware to work.

    """
    pass
