"""Tests for the Celery integration (issue #67)."""

import uuid

import pytest

celery = pytest.importorskip("celery")

from celery import states  # noqa: E402
from celery.app.trace import build_tracer  # noqa: E402
from celery.signals import before_task_publish, task_prerun  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from django.db import connection  # noqa: E402
from django.test import TransactionTestCase  # noqa: E402

from django_rls.context import (  # noqa: E402
    _active_context,
    _context_source,
    _identity_locked,
    get_active_rls_context,
    get_rls_context,
    set_rls_context,
    system_rls_context,
)
from django_rls.contrib.celery import (  # noqa: E402
    HEADER_NAME,
    RLSTask,
    connect_celery_signals,
    disconnect_celery_signals,
)
from tests.models import UserOwnedModel  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_context():
    _active_context.set({})
    _identity_locked.set(False)
    _context_source.set(None)
    yield
    _active_context.set({})
    _identity_locked.set(False)
    _context_source.set(None)


def make_app():
    # No Django fixup: it closes DB connections around every task, which the
    # test database connection cannot survive outside TransactionTestCase.
    return celery.Celery(
        "rls_tests",
        broker="memory://",
        backend="cache+memory://",
        fixups=[],
        set_as_current=False,
        task_cls=RLSTask,
    )


def run_in_worker(task, args=(), kwargs=None, headers=None):
    """Execute ``task`` the way a worker does, with the given message headers."""
    task_id = str(uuid.uuid4())
    request = {"id": task_id, "task": task.name, **(headers or {})}
    tracer = build_tracer(task.name, task, app=task.app, eager=False)
    result = tracer(task_id, list(args), kwargs or {}, request)
    if result.info is not None and result.info.state == states.FAILURE:
        raise result.retval.exception
    return result.retval


@pytest.fixture
def published_headers():
    captured = []

    def capture(sender=None, headers=None, **kwargs):
        captured.append(dict(headers))

    connect_celery_signals()
    # Connected after django_rls's receiver, so it sees the final headers.
    before_task_publish.connect(capture, weak=False)
    yield captured
    before_task_publish.disconnect(capture)
    disconnect_celery_signals()


@pytest.mark.django_db
def test_publish_attaches_active_context(require_postgresql, published_headers):
    app = make_app()

    @app.task
    def noop():
        pass

    with system_rls_context(user_id=5, tenant_id=2):
        noop.delay()

    assert published_headers[-1][HEADER_NAME] == {"user_id": "5", "tenant_id": "2"}


@pytest.mark.django_db
def test_publish_without_context_adds_no_header(require_postgresql, published_headers):
    app = make_app()

    @app.task
    def noop():
        pass

    noop.delay()

    assert HEADER_NAME not in published_headers[-1]


@pytest.mark.django_db
def test_explicit_header_is_not_overwritten(require_postgresql, published_headers):
    app = make_app()

    @app.task
    def noop():
        pass

    with system_rls_context(user_id=5):
        noop.apply_async(headers={HEADER_NAME: {"tenant_id": "9"}})

    assert published_headers[-1][HEADER_NAME] == {"tenant_id": "9"}


@pytest.mark.django_db
def test_disconnect_stops_propagation(require_postgresql, published_headers):
    app = make_app()

    @app.task
    def noop():
        pass

    disconnect_celery_signals()
    with system_rls_context(user_id=5):
        noop.delay()

    assert HEADER_NAME not in published_headers[-1]


@pytest.mark.django_db
def test_worker_runs_task_under_header_context(require_postgresql):
    app = make_app()

    @app.task
    def whoami():
        return get_rls_context("user_id"), get_rls_context("tenant_id")

    result = run_in_worker(
        whoami, headers={HEADER_NAME: {"user_id": "5", "tenant_id": "2"}}
    )

    assert result == ("5", "2")
    assert get_active_rls_context() == {}
    assert get_rls_context("user_id") is None


@pytest.mark.django_db
def test_worker_reads_header_from_request_headers(require_postgresql):
    app = make_app()

    @app.task
    def whoami():
        return get_rls_context("user_id")

    result = run_in_worker(whoami, headers={"headers": {HEADER_NAME: {"user_id": "8"}}})

    assert result == "8"


@pytest.mark.django_db
def test_worker_does_not_leak_previous_tasks_context(require_postgresql):
    app = make_app()

    @app.task
    def whoami():
        return get_rls_context("user_id")

    set_rls_context("user_id", 100, system=True)

    assert run_in_worker(whoami) is None


@pytest.mark.django_db
def test_worker_clears_context_when_task_fails(require_postgresql):
    app = make_app()

    @app.task
    def fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_in_worker(fail, headers={HEADER_NAME: {"user_id": "5"}})

    assert get_rls_context("user_id") is None


@pytest.mark.django_db
def test_malformed_header_fails_the_task(require_postgresql):
    app = make_app()
    ran = []

    @app.task
    def job():
        ran.append(True)

    with pytest.raises(ValueError):
        run_in_worker(job, headers={HEADER_NAME: {"bad key": "1"}})

    assert ran == []


@pytest.mark.django_db
def test_bound_task_keeps_its_request(require_postgresql):
    app = make_app()

    @app.task(bind=True)
    def my_id(self):
        return self.request.id, get_rls_context("user_id")

    task_id, user_id = run_in_worker(my_id, headers={HEADER_NAME: {"user_id": "3"}})

    assert task_id is not None
    assert user_id == "3"


@pytest.mark.django_db
def test_eager_and_direct_calls_keep_callers_context(require_postgresql):
    app = make_app()

    @app.task
    def whoami():
        return get_rls_context("user_id")

    set_rls_context("user_id", 7, system=True)

    assert whoami() == "7"
    assert whoami.apply().get() == "7"
    assert get_rls_context("user_id") == "7"


class TestCeleryRowFiltering(TransactionTestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice")
        self.bob = User.objects.create_user("bob")
        with system_rls_context(user_id=self.alice.id):
            UserOwnedModel.objects.create(title="a", content="", owner=self.alice)
        with system_rls_context(user_id=self.bob.id):
            UserOwnedModel.objects.create(title="b", content="", owner=self.bob)

    def test_context_survives_connection_close_before_task(self):
        """Celery's Django fixup closes DB connections in ``task_prerun``;
        the context must be applied after that, not lost with the session."""

        def close_connection(**kwargs):
            connection.close()

        task_prerun.connect(close_connection, weak=False)
        self.addCleanup(task_prerun.disconnect, close_connection)

        app = make_app()

        @app.task
        def list_titles():
            return list(UserOwnedModel.objects.values_list("title", flat=True))

        headers = {HEADER_NAME: {"user_id": str(self.alice.id)}}
        assert run_in_worker(list_titles, headers=headers) == ["a"]
        assert run_in_worker(list_titles) == []
