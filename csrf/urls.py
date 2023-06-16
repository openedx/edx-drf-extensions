"""
URLs for the CSRF application.
"""

from django.urls import path
from django.urls import include


urlpatterns = [
    path('csrf/api/', include('csrf.api.urls'), name='csrf_api'),
]
