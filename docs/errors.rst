Errors
======
ADR 0029 standardized error responses: the exception handler and its envelope
formatters, the ``Conflict`` exception, the error-type URI catalog with its
``register_error_type`` extension helper, and the ``ErrorResponseSerializer``
that documents the envelope in OpenAPI schemas. The handler delegates to a
base handler resolved from the
``EDX_DRF_EXTENSIONS['STANDARDIZED_ERROR_BASE_HANDLER']`` setting, so services
keep their own error-monitoring behavior.

.. automodule:: edx_rest_framework_extensions.errors
    :members:
