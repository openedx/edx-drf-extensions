Scoping
=======
OEP-66 record-visibility building blocks for DRF list endpoints: a
``ScopingPolicy`` structural interface (a ``typing.Protocol``), a
``ScopedQuerysetMixin`` that applies a configured policy in ``get_queryset()``,
and a ``FullScopePolicy`` for endpoints whose callers may see every row.

.. automodule:: edx_rest_framework_extensions.scoping
    :members:
