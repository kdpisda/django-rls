"""
Security Test: Transaction Scope and Autocommit

This test verifies that the library handles transaction scopes correctly.
Django runs in autocommit mode by default, meaning each statement is a transaction.
If `set_config` is called with `is_local=True`, it only lasts for the current transaction (the set_config call itself),
and is immediately lost for the next query.
"""
import pytest
from unittest.mock import Mock, patch, call
from django.test import SimpleTestCase
from django_rls.db.functions import set_rls_context, SetConfig

class TestTransactionScope(SimpleTestCase):
    
    @patch('django_rls.db.functions.connection')
    def test_set_context_uses_session_scope_by_default(self, mock_conn):
        """
        Critical Correctness Test:
        To support Django's default autocommit mode, set_config MUST use is_local=False (Session scope).
        If is_local=True, the context is lost immediately after the set_config SQL executes.
        """
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Call the function
        set_rls_context('user_id', '123')
        
        # Check arguments. 
        # The signature is set_config(name, value, is_local)
        # We expect is_local to be False for this to work in autocommit mode.
        
        # Current implementation hardcodes is_local=True in the function signature or call site.
        # We need to inspect what was actually passed to the SQL.
        
        calls = mock_cursor.execute.call_args_list
        assert len(calls) > 0
        args, kwargs = calls[0]
        sql, params = args
        
        # Params: [key, value, is_local]
        is_local_param = params[2]
        
        if is_local_param is True:
            pytest.fail("Design Flaw: is_local=True used! This breaks RLS in default autocommit mode.")
            
        assert is_local_param is False, "Should use session scope (is_local=False)"
