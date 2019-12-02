"""
App for documenting REST API views,
generating API spec files from them,
and then serving those API specs as a UI.

Under the hood, this app uses drf-yasg
("Yet Another Swagger Generator for DRF")
to generate API spec. It then uses Swagger to serve that spec.
"""
from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig


class EdxApiDocToolsConfig(AppConfig):
    """
    Configuration for this app.
    """
    name = 'edx_api_doc_tools'
    verbose_name = 'edX REST API Documentation Tools'
