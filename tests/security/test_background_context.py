"""
Regression tests: background jobs and worker RLS context.

HTTP middleware does not run in Celery/async workers — applications must use
``system_rls_context()`` with server-derived identity and reset pooled connections.
"""

import pytest
from django.test import override_settings

from django_rls.context import (
    clear_rls_context,
    get_active_rls_context,
    reset_connection_rls_context,
    set_rls_context,
    system_rls_context,
)
from django_rls.db.functions import get_rls_context
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
@pytest.mark.django_db
def test_background_job_sets_identity_via_system_rls_context(require_postgresql):
    with system_rls_context(user_id=42, tenant_id=7):
        ctx = get_active_rls_context()
        assert ctx["user_id"] == "42"
        assert ctx["tenant_id"] == "7"
        assert get_rls_context("user_id") == "42"
        assert get_rls_context("tenant_id") == "7"


@pytest.mark.security
@pytest.mark.django_db
def test_task_arguments_cannot_override_identity_without_system(require_postgresql):
    set_rls_context("user_id", 1, system=True)
    with pytest.raises(RLSContextImmutableError):
        set_rls_context("user_id", 999)


@pytest.mark.security
@pytest.mark.django_db
@override_settings(DJANGO_RLS={"REQUIRE_CONTEXT": True})
def test_background_query_requires_system_context(require_postgresql):
    from tests.models import UserOwnedModel

    with pytest.raises(RLSContextRequiredError):
        UserOwnedModel.objects.count()


@pytest.mark.security
@pytest.mark.django_db
@override_settings(DJANGO_RLS={"REQUIRE_CONTEXT": True})
def test_background_query_succeeds_inside_system_rls_context(require_postgresql):
    from tests.models import UserOwnedModel

    with system_rls_context(user_id=5):
        assert UserOwnedModel.objects.count() == 0


@pytest.mark.security
@pytest.mark.django_db
def test_worker_resets_stale_context_before_next_job(require_postgresql):
    set_rls_context("user_id", 100, system=True)
    reset_connection_rls_context()

    assert get_active_rls_context() == {}
    assert get_rls_context("user_id") in (None, "")

    with system_rls_context(user_id=200):
        assert get_active_rls_context()["user_id"] == "200"
        assert get_rls_context("user_id") == "200"


@pytest.mark.security
@pytest.mark.django_db
def test_explicit_clear_between_jobs_prevents_identity_leak(require_postgresql):
    set_rls_context("user_id", 10, system=True)
    set_rls_context("tenant_id", 99, system=True)

    clear_rls_context()

    assert get_active_rls_context() == {}
    assert get_rls_context("user_id") in (None, "")
    assert get_rls_context("tenant_id") in (None, "")

    with system_rls_context(user_id=11):
        assert "tenant_id" not in get_active_rls_context()


@pytest.mark.security
@pytest.mark.django_db
def test_system_context_restores_after_worker_scope(require_postgresql):
    set_rls_context("user_id", 1, system=True)

    with system_rls_context(user_id=50):
        assert get_active_rls_context()["user_id"] == "50"
        assert get_rls_context("user_id") == "50"

    assert get_active_rls_context()["user_id"] == "1"
    assert get_rls_context("user_id") == "1"