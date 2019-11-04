"""
URL definitions for version 1 of the CSRF API.
"""

from django.conf.urls import url

from .views import CsrfTokenView


urlpatterns = [
    url(r'^token$', CsrfTokenView.as_view(), name='csrf_token'),
]
