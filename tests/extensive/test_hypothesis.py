
"""
Extensive Property-Based Tests using Hypothesis.

This module uses fuzzing to generate random combinations of:
- Users
- Tenants
- Data
- Context Switches

To verify that RLS invariants hold true under all conditions.
"""
import pytest
from unittest.mock import Mock, patch
from hypothesis import given, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize
from django.test import SimpleTestCase, TransactionTestCase
from django.db import connection

from django_rls.expressions import RLSExpression
from django_rls.middleware import RLSContextMiddleware

# Strategies for generating random IDs and names
tenant_ids = st.integers(min_value=1, max_value=100000)
user_ids = st.integers(min_value=1, max_value=1000000)
names = st.text(min_size=1, max_size=100)

class TestFuzzingRLS(SimpleTestCase):

    @settings(max_examples=1000)
    @given(tenant_id=tenant_ids, user_id=user_ids)
    def test_invariant_context_setting(self, tenant_id, user_id):
        """
        Invariant: set_rls_context must always produce a valid SQL command 
        with properly escaped values, regardless of input.
        """
        # We mock the DB connection to verify the SQL generated
        with patch('django_rls.db.functions.connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            
            from django_rls.db.functions import set_rls_context
            
            set_rls_context('user_id', user_id, is_local=False)
            
            # Verify SQL structure
            calls = mock_cursor.execute.call_args_list
            assert len(calls) == 1
            sql, params = calls[0][0]
            
            # Check params
            assert params[0] == 'rls.user_id'
            assert params[1] == str(user_id)
            assert params[2] is False # Session scope (fixed vulnerability)

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
