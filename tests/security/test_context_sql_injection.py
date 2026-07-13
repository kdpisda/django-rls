"""
Regression tests: SQL injection via RLS session context (set_config).

Context values must always be passed as query parameters, never interpolated.
"""

from unittest.mock import Mock, patch

import pytest

from django_rls.context import set_rls_context
from django_rls.db.functions import get_rls_context
from django_rls.expressions import RLSExpression, RLSQuery

CONTEXT_SET_CONFIG_PAYLOADS = [
    "1'; DROP TABLE users; --",
    "'; DROP TABLE abc; --",
    "1; SELECT pg_sleep(10)",
    "0 OR 1=1",
    "NULL; TRUNCATE secrets",
]

RLS_EXPRESSION_QUOTE_PAYLOADS = [
    "1'; DROP TABLE users; --",
    "'; DROP TABLE abc; --",
    "it's a trap'; DROP TABLE t; --",
]


@pytest.mark.security
@pytest.mark.parametrize("malicious_value", CONTEXT_SET_CONFIG_PAYLOADS)
@patch("django_rls.context.connection")
def test_set_rls_context_uses_parameterized_query(mock_connection, malicious_value):
    mock_cursor = Mock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    set_rls_context("user_id", malicious_value, system=True)

    mock_cursor.execute.assert_called_once_with(
        "SELECT set_config(%s, %s, %s)",
        ["rls.user_id", str(malicious_value), False],
    )


@pytest.mark.security
@pytest.mark.parametrize("key", ["user_id", "tenant_id", "user_email"])
@patch("django_rls.context.connection")
def test_get_rls_context_uses_parameterized_query(mock_connection, key):
    mock_cursor = Mock()
    mock_cursor.fetchone.return_value = (None,)
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    get_rls_context(key)

    mock_cursor.execute.assert_called_once_with(
        "SELECT current_setting(%s, true)",
        [f"rls.{key}"],
    )


@pytest.mark.security
@pytest.mark.parametrize("malicious_value", RLS_EXPRESSION_QUOTE_PAYLOADS)
def test_rls_expression_escapes_single_quotes(malicious_value):
    formatted = RLSExpression("dummy")._format_value(malicious_value)

    assert formatted != f"'{malicious_value}'"
    assert formatted == f"'{malicious_value.replace(chr(39), chr(39) * 2)}'"


@pytest.mark.security
def test_has_permission_rejects_malicious_codename():
    with pytest.raises(ValueError, match="Invalid permission codename"):
        RLSQuery.has_permission("drop table users; --")


@pytest.mark.security
def test_has_permission_rejects_malicious_table_name():
    with pytest.raises(ValueError, match="Invalid permission table name"):
        RLSQuery.has_permission("view_user", permission_table="users; DROP TABLE x")


@pytest.mark.security
def test_has_permission_does_not_embed_drop_table_in_sql():
    sql = RLSQuery.has_permission("view_user")
    assert "DROP TABLE" not in sql
    assert "view_user" in sql
