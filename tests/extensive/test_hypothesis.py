"""
Extensive Property-Based Tests using Hypothesis.

This module uses fuzzing to generate random combinations of:
- Users
- Tenants
- Data
- Context Switches

To verify that RLS invariants hold true under all conditions.
"""
from django.db import connection
from django.test import SimpleTestCase
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase as HypothesisDjangoTestCase
from hypothesis.stateful import RuleBasedStateMachine, initialize, rule

from django_rls.expressions import RLSExpression
from django_rls.middleware import RLSContextMiddleware

# Strategies for generating random IDs and names
tenant_ids = st.integers(min_value=1, max_value=100000)
user_ids = st.integers(min_value=1, max_value=1000000)
names = st.text(min_size=1, max_size=100)


class TestFuzzingRLSPostgres(HypothesisDjangoTestCase):
    @settings(max_examples=100)
    @given(tenant_id=tenant_ids, user_id=user_ids)
    def test_invariant_context_setting(self, tenant_id, user_id):
        """
        Invariant: set_rls_context round-trips arbitrary values through PostgreSQL
        without corruption and keeps session scope across cursor boundaries.
        """
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL required")

        from django_rls.context import clear_rls_context
        from django_rls.db.functions import get_rls_context, set_rls_context

        set_rls_context("user_id", user_id, is_local=False, system=True)
        set_rls_context("tenant_id", tenant_id, is_local=False, system=True)

        assert get_rls_context("user_id") == str(user_id)
        assert get_rls_context("tenant_id") == str(tenant_id)

        clear_rls_context()


class TestFuzzingRLS(SimpleTestCase):
    @settings(max_examples=1000)
    @given(val=st.text())
    def test_invariant_expression_escaping(self, val):
        """
        Invariant: Any string value passed to an expression builder
        must be escaped if it contains quotes.
        """
        builder = RLSExpression("dummy")
        result = builder._format_value(val)

        # Must start and end with single quotes
        assert result.startswith("'")
        assert result.endswith("'")

        # Inner content must have escaped quotes
        inner = result[1:-1]

        expected = val.replace("'", "''")
        assert inner == expected

    @settings(max_examples=1000)
    @given(field=st.text(min_size=1), value=st.text())
    def test_custom_policy_construction_fuzzing(self, field, value):
        """
        Fuzzing Policy construction to ensure no crashes on weird strings.
        """
        # Construction shouldn't crash
        try:
            expr = RLSExpression(field)
            sql = expr._format_value(value)
            assert isinstance(sql, str)
        except Exception as e:
            # We only expect specific errors if validation fails,
            # but currently RLSExpression is lenient.
            # If it crashes with IndexError/TypeError, that's a find.
            raise e
