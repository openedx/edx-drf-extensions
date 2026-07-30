"""
OEP-66 queryset-scoping building blocks for DRF list endpoints.

`OEP-66`_ ("Separating Authorization Concerns in List Endpoints") prescribes
keeping three authorization concerns separate on a list endpoint, each handled
by a dedicated layer:

* **Endpoint access** -- DRF ``permission_classes`` (may this subject call the
  endpoint at all?). Returns ``403`` when denied.
* **Record visibility (queryset scoping)** -- a :class:`ScopingPolicy` applied
  in ``get_queryset()`` by :class:`ScopedQuerysetMixin` (which rows may this
  subject see?). Rows the subject may not see are simply absent from the
  response; their absence is never a ``403``.
* **User-driven filtering** -- e.g. a ``django-filter`` ``FilterSet`` (of the
  visible rows, which did the caller ask for?). Narrows an already-authorized
  queryset and must never widen it.

This module provides the reusable record-visibility layer: a structural
:class:`ScopingPolicy` interface and a :class:`ScopedQuerysetMixin` that applies
it. It is deliberately engine-agnostic -- a policy typically resolves the
subject's accessible scopes in one bulk lookup (for example openedx-authz
``get_scopes_for_subject_and_permission``) and turns that scope set into a
``WHERE`` clause, rather than running an ``enforce``-style check on every row --
but any object that can filter a queryset for a subject may implement it.

``ScopingPolicy`` is a :class:`typing.Protocol` rather than an abstract base
class: implementers do not import or inherit anything, and type checkers verify
conformance statically. :class:`ScopedQuerysetMixin` performs a lightweight
duck-typed check (does the configured policy expose a callable ``scope``?) at
runtime.

This is *application-level* queryset scoping, not database-enforced
`row-level security`_: it only constrains queries that go through the view's
scoped queryset; code that queries the model directly is not protected by it.

.. _OEP-66: https://docs.openedx.org/projects/openedx-proposals/en/latest/best-practices/oep-0066-bp-authorization.html
.. _row-level security: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
"""
from typing import Any, Optional, Protocol

from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet


class ScopingPolicy(Protocol):
    """
    Structural interface for an OEP-66 record-visibility policy.

    Any object exposing a compatible ``scope`` method satisfies this protocol --
    implementers need not import or inherit from it. It documents the expected
    interface for static type checkers; :class:`ScopedQuerysetMixin` verifies a
    configured policy with a lightweight duck-typed check at runtime.

    A policy must not re-implement access rules; it delegates to the platform's
    authorization engine to resolve the subject's accessible scopes and
    translates that answer into a queryset filter. Keeping it separate from the
    view lets the same visibility rule be reused and unit-tested on its own.
    """

    def scope(self, queryset: QuerySet, subject: Any) -> QuerySet:
        """Return ``queryset`` filtered to the rows visible to ``subject``."""


class ScopedQuerysetMixin:
    """
    Applies :attr:`scoping_policy` to a DRF view's base queryset (OEP-66).

    Mix into a ``GenericAPIView`` / ``ListAPIView`` (or ``GenericViewSet``) and
    set :attr:`scoping_policy` to any object implementing the
    :class:`ScopingPolicy` protocol. The mixin runs the policy on top of the
    view's ``get_queryset()`` result so the ``list`` response contains only the
    rows within the requesting subject's accessible scopes.
    """

    #: An object implementing the :class:`ScopingPolicy` protocol.
    scoping_policy: Optional[ScopingPolicy] = None

    def get_queryset(self) -> QuerySet:
        """Return the base queryset scoped to the rows the requesting subject may see."""
        queryset = super().get_queryset()
        policy = self.scoping_policy
        if not callable(getattr(policy, "scope", None)):
            raise ImproperlyConfigured(
                f"{type(self).__name__} uses ScopedQuerysetMixin but its scoping_policy does not "
                f"implement the ScopingPolicy protocol (expected a callable 'scope(queryset, subject)' method)."
            )
        return policy.scope(queryset, self.request.user)
