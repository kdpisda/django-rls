"""Celery integration: propagate RLS context from publisher to worker.

Two pieces, both set up where the Celery app is configured (usually
``proj/celery.py``)::

    from celery import Celery
    from django_rls.contrib.celery import RLSTask, connect_celery_signals

    app = Celery("proj", task_cls=RLSTask)
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()
    connect_celery_signals()

* :func:`connect_celery_signals` attaches the active RLS context (e.g. the one
  ``RLSContextMiddleware`` set for the current request) to every published
  task message, in the ``django_rls_context`` header.
* :class:`RLSTask` — the base class for tasks, app-wide via ``task_cls`` or
  per task via ``@shared_task(base=RLSTask)`` — runs each task under exactly
  the context from that header: the worker connection's context is cleared
  before the task and again after it. Tasks published without context
  (periodic Beat tasks, for example) run with an empty context and should
  establish their own with ``system_rls_context()``.

Context is applied when the task body is invoked rather than from a
``task_prerun`` signal handler, because Celery's Django fixup closes database
connections in its own ``task_prerun`` handler, which would discard it.

The header can also be set explicitly to run a task under a given context::

    export_tenant.apply_async(
        args=[tenant_id], headers={"django_rls_context": {"tenant_id": tenant_id}}
    )

The header is applied as a privileged (``system=True``) context switch, so the
message broker must be trusted — as it already is, since anyone who can publish
to it can run arbitrary tasks.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from celery import Task, current_task
from celery.signals import before_task_publish

from django_rls.tasks import capture_rls_context, task_rls_context

HEADER_NAME = "django_rls_context"

_DISPATCH_UID = "django_rls.contrib.celery"


def _on_before_task_publish(
    sender: Any = None, headers: Optional[Dict[str, Any]] = None, **kwargs: Any
) -> None:
    if headers is None or HEADER_NAME in headers:
        return
    context: Optional[Dict[str, Any]] = capture_rls_context()
    if not context:
        # Celery publishes chain successors and link callbacks after the task
        # body has returned (and its context has been cleared), while the task
        # is still the current one: pass its context on.
        context = _current_worker_task_context()
    if context:
        headers[HEADER_NAME] = context


def _current_worker_task_context() -> Optional[Dict[str, Any]]:
    task = current_task._get_current_object()
    if task is None or task.request.called_directly:
        return None
    return get_task_rls_context(task.request)


def get_task_rls_context(request: Any) -> Optional[Dict[str, Any]]:
    """Return the RLS context carried by a task request, if any."""
    # Celery merges custom message headers into the request itself; some
    # versions and protocols keep them under ``request.headers`` instead.
    context = getattr(request, HEADER_NAME, None)
    if context is None:
        context = (getattr(request, "headers", None) or {}).get(HEADER_NAME)
    return context


class RLSTask(Task):
    """Celery task base class that runs under the propagated RLS context.

    Only executions by a worker are affected. Calling the task function
    directly or eagerly (``task_always_eager``, ``.apply()``) runs inline under
    the caller's context, like any other function call.
    """

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        request = self.request
        if request.called_directly:
            return super().__call__(*args, **kwargs)
        # The tracer has already pushed the request, so call ``run`` directly
        # (as Celery does for tasks without a custom ``__call__``).
        if request.is_eager:
            return self.run(*args, **kwargs)

        # A worker has no caller whose context needs restoring; anything
        # still on the connection is leftover state and is discarded.
        with task_rls_context(
            get_task_rls_context(request), source="celery", restore=False
        ):
            return self.run(*args, **kwargs)


def connect_celery_signals() -> None:
    """Attach the active RLS context to published tasks. Idempotent."""
    before_task_publish.connect(
        _on_before_task_publish, dispatch_uid=_DISPATCH_UID, weak=False
    )


def disconnect_celery_signals() -> None:
    """Undo :func:`connect_celery_signals`."""
    before_task_publish.disconnect(_on_before_task_publish, dispatch_uid=_DISPATCH_UID)
