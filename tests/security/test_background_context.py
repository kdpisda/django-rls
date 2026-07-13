"""
Regression tests: background jobs and worker RLS context.

HTTP middleware does not run in Celery/async workers — applications must use
``system_rls_context()`` with server-derived identity and reset pooled connections.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from django.test import override_settings

from django_rls.context import (
    clear_rls_context,
    get_active_rls_context,
    reset_connection_rls_context,
    set_rls_context,
    system_rls_context,
)
from django_rls.exceptions import RLSContextImmutableError, RLSContextRequiredError


@pytest.fixture(autouse=True)
def _reset_context():
    from django_rls.context import _active_context, _context_source, _identity_locked

    _active_context.set({})
    _identity_locked.set(False)
    _context_source.set(None)
    yield
    _active_context.set({})
    _identity_locked.set(False)
    _context_source.set(None)


@pytest.mark.security
@patch("django_rls.context.connection")
def test_background_job_sets_identity_via_system_rls_context(_mock_conn):
    """Recommended worker pattern: privileged scope with server-derived IDs."""
    with system_rls_context(user_id=42, tenant_id=7):
        ctx = get_active_rls_context()
        assert ctx["user_id"] == "42"
        assert ctx["tenant_id"] == "7"


@pytest.mark.security
@patch("django_rls.context.connection")
def test_task_arguments_cannot_override_identity_without_system(_mock_conn):
    """Untrusted task args must not replace an established identity."""
    set_rls_context("user_id", 1, system=True)
    with pytest.raises(RLSContextImmutableError):
        set_rls_context("user_id", 999)


@pytest.mark.security
@override_settings(DJANGO_RLS={"REQUIRE_CONTEXT": True})
@patch("django_rls.context.connection")
def test_background_query_requires_system_context(_mock_conn):
    from tests.models import UserOwnedModel

    with pytest.raises(RLSContextRequiredError):
        UserOwnedModel.objects.count()


@pytest.mark.security
@override_settings(DJANGO_RLS={"REQUIRE_CONTEXT": True})
@patch("django_rls.context.connection")
def test_background_query_succeeds_inside_system_rls_context(_mock_conn):
    from tests.models import UserOwnedModel

    with system_rls_context(user_id=5):
        with patch.object(
            UserOwnedModel.objects, "count", return_value=0
        ) as mock_count:
            assert UserOwnedModel.objects.count() == 0
            mock_count.assert_called_once()


@pytest.mark.security
@patch("django_rls.context.connection")
def test_worker_resets_stale_context_before_next_job(_mock_conn):
    """Simulate pooled connection retaining identity from a prior job."""
    _mock_conn.vendor = "postgresql"

    set_rls_context("user_id", 100, system=True)
    reset_connection_rls_context()

    assert get_active_rls_context() == {}

    with system_rls_context(user_id=200):
        assert get_active_rls_context()["user_id"] == "200"


@pytest.mark.security
@patch("django_rls.context.connection")
def test_explicit_clear_between_jobs_prevents_identity_leak(_mock_conn):
    set_rls_context("user_id", 10, system=True)
    set_rls_context("tenant_id", 99, system=True)

    clear_rls_context()

    assert get_active_rls_context() == {}
    with system_rls_context(user_id=11):
        assert "tenant_id" not in get_active_rls_context()


@pytest.mark.security
@patch("django_rls.context.connection")
def test_system_context_restores_after_worker_scope(_mock_conn):
    mock_cursor = MagicMock()
    _mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = ("1",)

    set_rls_context("user_id", 1, system=True)

    with system_rls_context(user_id=50):
        assert get_active_rls_context()["user_id"] == "50"

    assert get_active_rls_context()["user_id"] == "1"
