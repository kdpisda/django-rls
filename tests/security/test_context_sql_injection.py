"""
Regression tests: SQL injection via RLS session context (set_config).

Context values must be stored literally in PostgreSQL session variables,
never executed as SQL.
"""

import pytest
from django.db import connection

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
@pytest.mark.django_db
@pytest.mark.parametrize("malicious_value", CONTEXT_SET_CONFIG_PAYLOADS)
def test_set_rls_context_stores_literal_value(require_postgresql, malicious_value):
    set_rls_context("user_id", malicious_value, system=True)

    assert get_rls_context("user_id") == str(malicious_value)

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1


@pytest.mark.security
@pytest.mark.django_db
@pytest.mark.parametrize("key", ["user_id", "tenant_id", "user_email"])
def test_get_rls_context_reads_registered_key(require_postgresql, key):
    set_rls_context(key, "safe-value", system=True)

    assert get_rls_context(key) == "safe-value"


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