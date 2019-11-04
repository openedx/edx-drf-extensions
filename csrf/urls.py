"""
URLs for the CSRF application.
"""

from django.conf.urls import include, url


urlpatterns = [
    url(r'^csrf/api/', include('csrf.api.urls'), name='csrf_api'),
]
