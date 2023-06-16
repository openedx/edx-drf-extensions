"""
URL definitions for the CSRF API endpoints.
"""

from django.urls import path
from django.urls import include


urlpatterns = [
    path('v1/', include('csrf.api.v1.urls'), name='csrf_api_v1'),
]
