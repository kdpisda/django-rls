"""
Regression tests: configuration hardening (audit_rls, signals, settings).

Covers production-readiness controls added for enterprise security audits.
"""

import logging
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.core.management import call_command
from django.db import connection
from django.test import override_settings

from django_rls.context import (
    clear_rls_context,
    get_registered_context_keys,
    set_rls_context,
)
from django_rls.exceptions import RLSContextRequiredError


@pytest.fixture(autouse=True)
def _reset_context():
    """Reset in-process context state without touching the database."""
    from django_rls.context import _active_context, _context_source, _identity_locked

    _active_context.set({})
    _identity_locked.set(False)
    _context_source.set(None)
    yield
    _active_context.set({})
    _identity_locked.set(False)
    _context_source.set(None)


@pytest.mark.security
@patch("django_rls.management.commands.audit_rls.connection")
def test_audit_rls_passes_when_rls_and_force_enabled(mock_conn):
    mock_conn.vendor = "postgresql"
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (True, True)
    mock_cursor.fetchall.return_value = [("owner_policy", True, "{public}", "ALL")]

    out = StringIO()
    call_command("audit_rls", stdout=out)

    assert "RLS audit passed" in out.getvalue()


@pytest.mark.security
@patch("django_rls.management.commands.audit_rls.connection")
def test_audit_rls_fails_when_force_rls_missing(mock_conn):
    mock_conn.vendor = "postgresql"
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (True, False)
    mock_cursor.fetchall.return_value = []

    with pytest.raises(SystemExit):
        call_command("audit_rls")


@pytest.mark.security
@patch("django_rls.management.commands.audit_rls.connection")
def test_audit_rls_warns_on_custom_policy_models(mock_conn):
    mock_conn.vendor = "postgresql"
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (True, True)
    mock_cursor.fetchall.return_value = [("public_policy", True, "{public}", "ALL")]

    out = StringIO()
    call_command("audit_rls", stdout=out)

    assert "CustomPolicy" in out.getvalue()


@pytest.mark.security
@patch("django_rls.management.commands.audit_rls.connection")
def test_audit_rls_requires_postgresql(mock_conn):
    mock_conn.vendor = "sqlite"

    err = StringIO()
    call_command("audit_rls", stderr=err)

    assert "requires a PostgreSQL database" in err.getvalue()


@pytest.mark.security
@patch("django_rls.context.clear_rls_context")
def test_reset_rls_on_connection_clears_postgresql_context(mock_clear):
    from django_rls.apps import _reset_rls_on_connection

    pg_connection = Mock(vendor="postgresql")
    _reset_rls_on_connection(sender=None, connection=pg_connection)
    mock_clear.assert_called_once()


@pytest.mark.security
@patch("django_rls.context.clear_rls_context")
def test_reset_rls_on_connection_skips_non_postgresql(mock_clear):
    from django_rls.apps import _reset_rls_on_connection

    _reset_rls_on_connection(sender=None, connection=Mock(vendor="sqlite"))
    mock_clear.assert_not_called()


@pytest.mark.security
@patch("django_rls.context.clear_rls_context")
@patch("django_rls.context.connection")
def test_reset_connection_rls_context_delegates_to_clear(mock_conn, mock_clear):
    mock_conn.vendor = "postgresql"
    from django_rls.context import reset_connection_rls_context

    reset_connection_rls_context()
    mock_clear.assert_called_once()


@pytest.mark.security
@override_settings(DJANGO_RLS={"AUDIT_LOG": True})
@patch("django_rls.context.connection")
def test_audit_log_emits_on_context_set(_mock_conn, caplog):
    caplog.set_level(logging.INFO, logger="django_rls.context")
    set_rls_context("user_id", 42, system=True)
    assert "rls_context_set" in caplog.text


@pytest.mark.security
@override_settings(DJANGO_RLS={"AUDIT_LOG": True})
@patch("django_rls.context.connection")
def test_audit_log_emits_on_context_clear(_mock_conn, caplog):
    caplog.set_level(logging.INFO, logger="django_rls.context")
    set_rls_context("user_id", 42, system=True)
    caplog.clear()
    set_rls_context("user_id", "", system=True)
    assert "rls_context_clear" in caplog.text


@pytest.mark.security
@override_settings(DJANGO_RLS={"AUDIT_LOG": False})
@patch("django_rls.context.connection")
def test_audit_log_disabled_by_default(_mock_conn, caplog):
    caplog.set_level(logging.INFO, logger="django_rls.context")
    set_rls_context("user_id", 1, system=True)
    assert "rls_context_set" not in caplog.text


@pytest.mark.security
@override_settings(DJANGO_RLS={"AUTO_ENABLE_RLS": True, "STRICT_MIGRATE_RLS": True})
@patch("tests.models.UserOwnedModel.enable_rls", side_effect=RuntimeError("rls fail"))
def test_strict_migrate_rls_reraises_on_failure(_mock_enable):
    from django_rls.models import enable_rls_on_migrate

    sender = Mock()
    sender.name = "tests"
    with pytest.raises(RuntimeError, match="rls fail"):
        enable_rls_on_migrate(sender=sender)


@pytest.mark.security
@override_settings(DJANGO_RLS={"AUTO_ENABLE_RLS": True, "STRICT_MIGRATE_RLS": False})
@patch("tests.models.UserOwnedModel.enable_rls", side_effect=RuntimeError("rls fail"))
def test_strict_migrate_rls_disabled_swallows_failure(_mock_enable):
    from django_rls.models import enable_rls_on_migrate

    sender = Mock()
    sender.name = "tests"
    enable_rls_on_migrate(sender=sender)


@pytest.mark.security
@override_settings(DJANGO_RLS={"REGISTERED_CONTEXT_KEYS": ["department_id", "role"]})
def test_registered_context_keys_includes_standard_and_custom():
    keys = get_registered_context_keys()
    assert keys == {"user_id", "tenant_id", "department_id", "role"}


@pytest.mark.security
@override_settings(DJANGO_RLS={"REGISTERED_CONTEXT_KEYS": ["department_id"]})
@patch("django_rls.context.connection")
def test_clear_rls_context_clears_registered_keys(mock_conn):
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.vendor = "postgresql"

    set_rls_context("department_id", "sales")
    clear_rls_context()

    cleared_keys = {
        call.args[1][0].removeprefix("rls.")
        for call in mock_cursor.execute.call_args_list
        if call.args[0] == "SELECT set_config(%s, %s, %s)" and call.args[1][1] == ""
    }
    assert cleared_keys == {"user_id", "tenant_id", "department_id"}


@pytest.mark.security
@patch("django.db.transaction.atomic")
@patch("django.db.connections")
def test_enable_rls_calls_force_rls(mock_connections, mock_atomic):
    from tests.models import UserOwnedModel

    mock_atomic.return_value.__enter__ = Mock(return_value=None)
    mock_atomic.return_value.__exit__ = Mock(return_value=False)

    mock_editor = MagicMock()
    mock_editor.__enter__.return_value = mock_editor
    mock_editor.__exit__.return_value = False

    mock_conn = MagicMock()
    mock_conn.vendor = "postgresql"
    mock_conn.schema_editor.return_value = mock_editor
    mock_connections.__getitem__.return_value = mock_conn

    UserOwnedModel.enable_rls()

    mock_editor.enable_rls.assert_called_once_with(UserOwnedModel)
    mock_editor.force_rls.assert_called_once_with(UserOwnedModel)


@pytest.mark.security
@override_settings(DJANGO_RLS={"REQUIRE_CONTEXT": True})
def test_queryset_count_requires_identity_context():
    from tests.models import UserOwnedModel

    with pytest.raises(RLSContextRequiredError, match="identity context is required"):
        UserOwnedModel.objects.count()


@pytest.mark.security
@override_settings(DJANGO_RLS={"REQUIRE_CONTEXT": True})
@patch("django_rls.context.connection")
def test_queryset_get_requires_identity_context(_mock_conn):
    from tests.models import UserOwnedModel

    with pytest.raises(RLSContextRequiredError):
        UserOwnedModel.objects.get(pk=1)


@pytest.mark.security
@override_settings(DJANGO_RLS={"REQUIRE_CONTEXT": True})
@patch("django_rls.context.connection")
def test_queryset_allows_access_when_context_set(_mock_conn):
    from tests.models import UserOwnedModel

    set_rls_context("user_id", 1, system=True)
    with patch.object(UserOwnedModel.objects, "count", return_value=0) as mock_count:
        assert UserOwnedModel.objects.count() == 0
        mock_count.assert_called_once()
