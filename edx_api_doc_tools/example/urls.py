"""
TODO
"""
from __future__ import absolute_import, unicode_literals

from rest_framework.routers import SimpleRouter

from .. import make_docs_urls
from .views import HedgehogViewSet


urlpatterns = []

ROUTER = SimpleRouter()
ROUTER.register(r'api/hedgehog/v0/hogs', HedgehogViewSet, basename='hedgehog')
urlpatterns += ROUTER.urls

urlpatterns += make_docs_urls(
    title="edX Hedgehog Service API",
    version="v0",
    email="hedgehog-support@example.com",
    description="A REST API for interacting with the edX hedgehog service.",
)
