"""
API for CSRF application.
"""

from django.middleware.csrf import get_token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication


class CsrfTokenView(APIView):
    """
        **Use Case**

            Allows frontend apps to obtain a CSRF token from the Django
            service in order to make POST, PUT, and DELETE requests to
            API endpoints hosted on the service.

        **Behavior**

            GET /csrf/api/v1/token
            >>> {
            >>>     "csrfToken": "abcdefg1234567"
            >>> }
    """

    authentication_classes = (JwtAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """
        GET /csrf/api/v1/token
        """
        return Response({'csrfToken': get_token(request)})
