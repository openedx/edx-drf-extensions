""" Tests for the OEP-66 queryset-scoping building blocks. """
from unittest.mock import Mock, sentinel

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from edx_rest_framework_extensions.scoping import ScopedQuerysetMixin


class _RecordingPolicy:
    """ A duck-typed policy (no inheritance) that records its ``scope`` call. """
    def __init__(self, result):
        self.result = result
        self.calls = []

    def scope(self, queryset, subject):
        self.calls.append((queryset, subject))
        return self.result


class _NotAPolicy:
    """ An object that does not expose a ``scope`` method. """


class ScopedQuerysetMixinTests(TestCase):
    """ Tests for ``ScopedQuerysetMixin.get_queryset``. """

    def _make_view(self, policy, base_queryset=sentinel.base_qs, user=sentinel.user):
        """ Build a mixin-based view whose ``super().get_queryset()`` yields ``base_queryset``. """
        base_request = Mock(user=user)

        class _BaseView:
            def get_queryset(self):
                return base_queryset

        class _View(ScopedQuerysetMixin, _BaseView):
            request = base_request
            scoping_policy = policy

        return _View()

    def test_applies_policy_to_base_queryset(self):
        # A plain duck-typed policy (no import/inheritance) is accepted and applied.
        policy = _RecordingPolicy(result=sentinel.scoped_qs)
        view = self._make_view(policy)

        result = view.get_queryset()

        self.assertIs(result, sentinel.scoped_qs)
        self.assertEqual(policy.calls, [(sentinel.base_qs, sentinel.user)])

    def test_missing_policy_raises_improperly_configured(self):
        view = self._make_view(policy=None)
        with self.assertRaises(ImproperlyConfigured):
            view.get_queryset()

    def test_policy_without_scope_raises_improperly_configured(self):
        view = self._make_view(policy=_NotAPolicy())
        with self.assertRaises(ImproperlyConfigured):
            view.get_queryset()

    def test_policy_with_non_callable_scope_raises_improperly_configured(self):
        view = self._make_view(policy=Mock(scope="not-callable"))
        with self.assertRaises(ImproperlyConfigured):
            view.get_queryset()
