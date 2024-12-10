"""
URL definitions for version 1 of the CSRF API.
"""

from django.urls import path

from .views import CsrfTokenView


urlpatterns = [
    path('token', CsrfTokenView.as_view(), name='csrf_token'),
]
