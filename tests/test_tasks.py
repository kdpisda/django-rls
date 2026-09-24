"""Tests for RLS context propagation into background tasks (issue #67)."""

import pytest
from django.contrib.auth.models import User
from django.test import TransactionTestCase

from django_rls.context import (
    _active_context,
    _context_source,
    _identity_locked,
    get_active_rls_context,
    get_rls_context,
    set_rls_context,
    system_rls_context,
)
from django_rls.tasks import (
    RLS_CONTEXT_KWARG,
    capture_rls_context,
    task_rls_context,
    with_rls_context,
)
from tests.models import UserOwnedModel

try:
    from django.tasks import task as django_task
except ImportError:  # Django < 6.0
    django_task = None

if django_task is not None:

    @django_task
    @with_rls_context
    def whoami_task():
        return get_rls_context("user_id")


@pytest.fixture(autouse=True)
def _reset_context():
    _active_context.set({})
    _identity_locked.set(False)
    _context_source.set(None)
    yield
    _active_context.set({})
    _identity_locked.set(False)
    _context_source.set(None)


@pytest.mark.django_db
def test_capture_returns_serializable_snapshot(require_postgresql):
    with system_rls_context(user_id=7, tenant_id=3):
        snapshot = capture_rls_context()

    assert snapshot == {"user_id": "7", "tenant_id": "3"}
    # A snapshot, not a live view of the active context.
    assert get_active_rls_context() == {}


@pytest.mark.django_db
def test_task_context_is_applied_and_cleared(require_postgresql):
    with task_rls_context({"user_id": 42, "tenant_id": "9"}) as ctx:
        assert ctx == {"user_id": "42", "tenant_id": "9"}
        assert get_rls_context("user_id") == "42"
        assert get_rls_context("tenant_id") == "9"

    assert get_active_rls_context() == {}
    assert get_rls_context("user_id") is None
    assert get_rls_context("tenant_id") is None


@pytest.mark.django_db
def test_task_does_not_inherit_stale_connection_context(require_postgresql):
    # Left behind by a previous task on the same worker connection.
    set_rls_context("user_id", 100, system=True)
    set_rls_context("department", "sales", system=True)

    with task_rls_context(None):
        assert get_active_rls_context() == {}
        assert get_rls_context("user_id") is None
        assert get_rls_context("department") is None


@pytest.mark.django_db
def test_task_overrides_protected_identity(require_postgresql):
    set_rls_context("user_id", 1, system=True)

    with task_rls_context({"user_id": 2}):
        assert get_rls_context("user_id") == "2"


@pytest.mark.django_db
def test_callers_context_is_restored_after_inline_task(require_postgresql):
    """In-process execution (eager Celery, django.tasks ImmediateBackend)
    must not clobber the caller's context."""
    set_rls_context("user_id", 1, system=True)
    set_rls_context("department", "sales", system=True)

    with task_rls_context({"user_id": 2, "project": "apollo"}):
        assert get_rls_context("department") is None

    assert get_active_rls_context() == {"user_id": "1", "department": "sales"}
    assert get_rls_context("user_id") == "1"
    assert get_rls_context("department") == "sales"
    assert get_rls_context("project") is None


@pytest.mark.django_db
def test_task_context_is_cleared_when_task_raises(require_postgresql):
    with pytest.raises(RuntimeError):
        with task_rls_context({"user_id": 5, "project": "apollo"}):
            raise RuntimeError("boom")

    assert get_active_rls_context() == {}
    assert get_rls_context("user_id") is None
    assert get_rls_context("project") is None


@pytest.mark.django_db
def test_empty_values_are_skipped(require_postgresql):
    with task_rls_context({"user_id": 5, "tenant_id": None, "project": ""}) as ctx:
        assert ctx == {"user_id": "5"}


@pytest.mark.parametrize(
    "context, error",
    [
        (["user_id", 1], TypeError),
        ("user_id=1", TypeError),
        ({"user id": 1}, ValueError),
        ({"user_id; DROP TABLE x": 1}, ValueError),
        ({1: 1}, ValueError),
    ],
)
@pytest.mark.django_db
def test_malformed_context_is_rejected(require_postgresql, context, error):
    set_rls_context("user_id", 1, system=True)

    with pytest.raises(error):
        with task_rls_context(context):
            pass  # pragma: no cover

    # Nothing was touched.
    assert get_rls_context("user_id") == "1"


@pytest.mark.django_db
def test_with_rls_context_decorator(require_postgresql):
    seen = {}

    @with_rls_context
    def build_report(report_id, *, fmt="pdf"):
        """Docstring."""
        seen["args"] = (report_id, fmt)
        seen["user_id"] = get_rls_context("user_id")
        return "done"

    with system_rls_context(user_id=11):
        snapshot = capture_rls_context()

    result = build_report(3, fmt="csv", **{RLS_CONTEXT_KWARG: snapshot})

    assert result == "done"
    assert seen == {"args": (3, "csv"), "user_id": "11"}
    assert build_report.__name__ == "build_report"
    assert build_report.__doc__ == "Docstring."
    assert get_rls_context("user_id") is None


@pytest.mark.django_db
def test_with_rls_context_without_snapshot_runs_with_no_identity(
    require_postgresql,
):
    @with_rls_context
    def job():
        return get_rls_context("user_id")

    set_rls_context("user_id", 1, system=True)

    assert job() is None
    assert get_rls_context("user_id") == "1"


@pytest.mark.skipif(django_task is None, reason="django.tasks requires Django 6.0+")
@pytest.mark.django_db
def test_django_tasks_immediate_backend(require_postgresql):
    set_rls_context("user_id", 1, system=True)

    with system_rls_context(user_id=21):
        snapshot = capture_rls_context()

    result = whoami_task.enqueue(**{RLS_CONTEXT_KWARG: snapshot})

    assert result.return_value == "21"
    # ImmediateBackend runs inline; the caller's context is restored.
    assert get_rls_context("user_id") == "1"


class TestTaskRowFiltering(TransactionTestCase):
    """The propagated context drives the actual RLS policies."""

    def setUp(self):
        self.alice = User.objects.create_user("alice")
        self.bob = User.objects.create_user("bob")
        with system_rls_context(user_id=self.alice.id):
            UserOwnedModel.objects.create(title="a", content="", owner=self.alice)
        with system_rls_context(user_id=self.bob.id):
            UserOwnedModel.objects.create(title="b", content="", owner=self.bob)

    def test_task_sees_only_the_enqueuing_users_rows(self):
        @with_rls_context
        def list_titles():
            return list(UserOwnedModel.objects.values_list("title", flat=True))

        with system_rls_context(user_id=self.alice.id):
            snapshot = capture_rls_context()

        assert list_titles(**{RLS_CONTEXT_KWARG: snapshot}) == ["a"]
        assert list_titles() == []
