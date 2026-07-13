"""
Regression tests: PostgreSQL-only behavior and operational limitations.

RLS is enforced by PostgreSQL — non-PG backends skip or warn. Documents
FORCE RLS, JOIN rewriting, and deployment constraints from SECURITY.md.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from django.db import models
from django.db.models import Q
from django.test import override_settings

from django_rls.backends.postgresql.base import RLSDatabaseSchemaEditor
from django_rls.conf import rls_config
from django_rls.models import RLSModel
from django_rls.policies import ModelPolicy, UserPolicy


class _UnsupportedSchemaEditor:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.mark.security
@override_settings(
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
)
def test_use_native_rls_false_without_postgresql_backend():
    assert rls_config.use_native_rls is False


@pytest.mark.security
@override_settings(
    DATABASES={"default": {"ENGINE": "django_rls.backends.postgresql", "NAME": "test"}}
)
def test_use_native_rls_true_with_rls_backend():
    assert rls_config.use_native_rls is True


@pytest.mark.security
@patch("django.db.connections")
def test_enable_rls_warns_on_unsupported_backend(mock_connections, caplog):
    from tests.models import UserOwnedModel

    mock_conn = MagicMock()
    mock_conn.vendor = "sqlite"
    mock_conn.schema_editor.return_value = _UnsupportedSchemaEditor()
    mock_connections.__getitem__.return_value = mock_conn

    UserOwnedModel.enable_rls()

    assert "does not support RLS" in caplog.text


@pytest.mark.security
@patch("django_rls.context.clear_rls_context")
def test_reset_connection_skips_non_postgresql(mock_clear):
    from django_rls.context import reset_connection_rls_context

    with patch("django_rls.context.connection") as mock_conn:
        mock_conn.vendor = "sqlite"
        reset_connection_rls_context()
        mock_clear.assert_not_called()


@pytest.mark.security
def test_schema_editor_force_rls_sql_prevents_owner_bypass():
    editor = RLSDatabaseSchemaEditor(Mock())
    assert "FORCE ROW LEVEL SECURITY" in editor.sql_force_rls


@pytest.mark.security
def test_user_policy_defaults_to_permissive():
    policy = UserPolicy("owner_policy", user_field="owner")
    assert policy.permissive is True


@pytest.mark.security
def test_restrictive_policy_can_deny_by_default():
    policy = UserPolicy("deny_default", user_field="owner", permissive=False)
    assert policy.permissive is False


@pytest.mark.security
def test_model_policy_rewrites_joins_to_subqueries():
    """Postgres RLS USING clauses cannot reference joined tables (issue #14)."""

    class _Company(models.Model):
        name = models.CharField(max_length=100)

        class Meta:
            app_label = "tests"

    class _Employee(RLSModel):
        name = models.CharField(max_length=100)
        company = models.ForeignKey(_Company, on_delete=models.CASCADE)

        class Meta:
            app_label = "tests"
            rls_policies = []

    policy = ModelPolicy("company_filter", filters=Q(company__name="Acme"))
    rewritten = policy._rewrite_filters(policy.filters, _Employee)

    assert any(
        lookup == "company_id__in"
        for lookup, _value in rewritten.children
        if isinstance(lookup, str)
    )


@pytest.mark.security
@patch("django_rls.management.commands.audit_rls.connection")
def test_audit_rls_reports_missing_table(mock_conn):
    mock_conn.vendor = "postgresql"
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []

    from io import StringIO

    from django.core.management import call_command

    with pytest.raises(SystemExit):
        call_command("audit_rls", stdout=StringIO(), stderr=StringIO())
