"""
App for documenting REST API views,
generating API spec files from them,
and then serving those API specs as a UI.

Uses drf-yasg ("Yet Another Swagger Generator for DRF")
to generate API spec. Uses Swagger to serve that spec.
"""

from django.apps import AppConfig


class EdxApiDocToolsConfig(AppConfig):
    """
    Configuration for this app.
    """
    name = 'edx_api_doc_tools'
    verbose_name = 'edX REST API Documentation Tools'
