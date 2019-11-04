"""
URL definitions for the CSRF API endpoints.
"""

from django.conf.urls import include, url


urlpatterns = [
    url(r'^v1/', include('csrf.api.v1.urls'), name='csrf_api_v1'),
]
