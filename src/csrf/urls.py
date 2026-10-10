"""
URLs for the CSRF application.
"""

from django.urls import include, path


urlpatterns = [
    path('csrf/api/', include('csrf.api.urls'), name='csrf_api'),
]
