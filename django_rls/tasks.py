"""RLS context propagation for background tasks.

HTTP middleware does not run in task workers (Celery, RQ, Dramatiq, Django's
``django.tasks`` framework, plain threads, ...), so the identity that was
active when a task was *enqueued* has to travel with the task and be
re-established when it *runs*.

This module is framework-agnostic:

* :func:`capture_rls_context` snapshots the active context so it can be sent
  along with a task (it is a plain ``dict`` of strings, safe for JSON).
* :func:`task_rls_context` is a context manager that runs a block with exactly
  that context — nothing leaks in from whatever ran before on the worker's
  database connection, and nothing leaks out to what runs after.
* :func:`with_rls_context` is a decorator that pops the snapshot from the
  ``_rls_context`` keyword argument and wraps the call in
  :func:`task_rls_context`.

For Celery, :mod:`django_rls.contrib.celery` does this automatically through
message headers, so task signatures need no changes.
"""

from __future__ import annotations

import functools
import re
from contextlib import contextmanager
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    TypeVar,
)

from django.db import connection

from django_rls.context import (
    apply_rls_context,
    clear_rls_context,
    get_active_rls_context,
    get_context_source,
)

RLS_CONTEXT_KWARG = "_rls_context"

_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

F = TypeVar("F", bound=Callable[..., Any])


def capture_rls_context() -> Dict[str, str]:
    """Return a serializable snapshot of the active RLS context.

    Call this where the task is enqueued (e.g. inside a view, where
    ``RLSContextMiddleware`` has already established the identity) and pass
    the result to the task.
    """
    return get_active_rls_context()


def _validate_context(context: Any) -> Dict[str, str]:
    if context is None:
        return {}
    if not isinstance(context, Mapping):
        raise TypeError(
            f"RLS task context must be a mapping, got {type(context).__name__}."
        )
    validated: Dict[str, str] = {}
    for key, value in context.items():
        if not isinstance(key, str) or not _KEY_RE.match(key):
            raise ValueError(f"Invalid RLS context key: {key!r}")
        if value is None or value == "":
            continue
        validated[key] = str(value)
    return validated


def _clear_scope(keys: Iterable[str]) -> None:
    if keys:
        clear_rls_context(set(keys))
    clear_rls_context()


@contextmanager
def task_rls_context(
    context: Optional[Mapping[str, Any]] = None,
    *,
    source: str = "task",
    restore: bool = True,
) -> Iterator[Dict[str, str]]:
    """Run a block with exactly ``context`` as the RLS context.

    On entry, any context already on the connection is cleared (so a worker
    never runs a task under the previous task's identity) and ``context`` is
    applied as a privileged (``system=True``) switch. On exit, the task's
    context is cleared.

    With ``restore=True`` (the default), whatever was active before is then
    re-applied. This keeps in-process execution (``django.tasks``
    ``ImmediateBackend``, direct calls) from clobbering the caller's context.
    In a worker process, where "whatever was active before" can only be state
    left behind by earlier code, pass ``restore=False`` so the connection is
    left empty.

    With no ``context`` the block runs with an empty context, which RLS
    policies treat as "no identity" (fail closed).
    """
    task_context = _validate_context(context)

    if connection.vendor != "postgresql":
        yield dict(task_context)
        return

    previous = get_active_rls_context()
    previous_source = get_context_source()

    _clear_scope(previous)
    try:
        apply_rls_context(task_context, system=True, source=source)
        yield get_active_rls_context()
    finally:
        _clear_scope(task_context)
        if restore and previous:
            apply_rls_context(
                previous, system=True, source=previous_source or "restore"
            )


def with_rls_context(func: Optional[F] = None, *, restore: bool = True) -> Any:
    """Decorate a task function so it runs under a propagated RLS context.

    The caller passes the snapshot through the ``_rls_context`` keyword
    argument, which is removed before ``func`` is called::

        @task  # django.tasks, Celery's @shared_task, RQ's @job, ...
        @with_rls_context
        def build_report(report_id):
            return Report.objects.get(pk=report_id).render()

        build_report.enqueue(42, _rls_context=capture_rls_context())

    Calls without ``_rls_context`` run with an empty context.

    By default the caller's context is restored afterwards, which inline
    backends need. For tasks that only ever run in a dedicated worker, use
    ``@with_rls_context(restore=False)`` so no leftover context survives the
    task (see :func:`task_rls_context`).
    """

    def decorate(f: F) -> F:
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            context = kwargs.pop(RLS_CONTEXT_KWARG, None)
            with task_rls_context(context, restore=restore):
                return f(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    if func is not None:
        return decorate(func)
    return decorate
