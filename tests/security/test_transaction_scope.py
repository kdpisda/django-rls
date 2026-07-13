"""
Security Test: Transaction Scope and Autocommit

``set_config`` must use session scope (``is_local=False``) so context survives
autocommit statement boundaries.
"""

from unittest.mock import Mock, patch

import pytest

from django_rls.context import set_rls_context


@pytest.mark.security
@patch("django_rls.context.connection")
def test_set_context_uses_session_scope_by_default(mock_conn):
    mock_cursor = Mock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    set_rls_context("user_id", "123", system=True)

    args, _kwargs = mock_cursor.execute.call_args
    _sql, params = args
    assert params[2] is False, "Must use session scope (is_local=False)"
