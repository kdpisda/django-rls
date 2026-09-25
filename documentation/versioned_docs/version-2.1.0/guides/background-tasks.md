---
sidebar_position: 5
---

# Background Tasks

`RLSContextMiddleware` only runs for HTTP requests. A task executed by a worker
(Celery, Django's `django.tasks`, RQ, Dramatiq, a thread pool, ...) starts with
**no** RLS context, so RLS policies hide every row from it.

django-rls lets the identity that was active when a task was **enqueued** travel
with the task and be re-established — and cleaned up again — when it **runs**.

## Celery

Two lines in the module that configures your Celery app:

```python
# proj/celery.py
from celery import Celery
from django_rls.contrib.celery import RLSTask, connect_celery_signals

app = Celery("proj", task_cls=RLSTask)
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

connect_celery_signals()
```

- `connect_celery_signals()` attaches the active context to every published task
  in the `django_rls_context` message header.
- `RLSTask` runs each task under exactly the context from that header. The
  worker connection's context is cleared before the task and again after it
  (also when it fails), so identity never leaks from one task to the next.

Tasks need no changes:

```python
from celery import shared_task

@shared_task
def export_documents(folder_id):
    # Sees only the rows the user who triggered the export can see.
    return list(Document.objects.filter(folder_id=folder_id).values())
```

```python
def export_view(request, folder_id):
    export_documents.delay(folder_id)  # context captured from the request
    ...
```

Chains, groups and link callbacks inherit the context too: a task published
while another task runs gets that task's context.

To use `RLSTask` for some tasks only, leave `task_cls` alone and pass it per task:
`@shared_task(base=RLSTask)`.

Calling a task directly (`export_documents(1)`) or eagerly (`.apply()`,
`CELERY_TASK_ALWAYS_EAGER`) runs it inline under the caller's context, like any
other function call.

### Tasks without a user

Periodic (Beat) tasks and tasks published outside a request run with an empty
context. Establish the identity inside the task from trusted data:

```python
from django_rls.context import system_rls_context

@shared_task
def nightly_digest():
    for tenant in Tenant.objects.all():
        with system_rls_context(tenant_id=tenant.id):
            send_digest(Document.objects.filter(updated_at__gte=yesterday()))
```

Or set the header explicitly when publishing:

```python
export_documents.apply_async(
    args=[folder_id],
    headers={"django_rls_context": {"tenant_id": str(tenant.id)}},
)
```

:::caution Trust
The header is applied as a privileged (`system=True`) context switch. Anyone who
can publish to your broker can already run arbitrary tasks, so the broker must
be trusted either way — but never build the header from user input.
:::

:::note Why a task base class?
Celery's Django integration closes database connections in its own
`task_prerun` handler, which would discard context set from a signal. `RLSTask`
applies the context when the task body is invoked, after that has happened.
:::

## Django tasks and other queues

For `django.tasks` (Django 6.0+) or any other queue, decorate the task with
`with_rls_context` and pass a snapshot of the context when enqueuing:

```python
from django.tasks import task
from django_rls.tasks import capture_rls_context, with_rls_context

@task
@with_rls_context
def build_report(report_id):
    return Report.objects.get(pk=report_id).render()

def report_view(request, report_id):
    build_report.enqueue(report_id, _rls_context=capture_rls_context())
```

`with_rls_context` removes the `_rls_context` keyword argument before calling the
function and runs it under that context. Without `_rls_context` the function runs
with an empty context.

Afterwards it clears the task's context and restores the caller's, because
inline backends such as Django's default `ImmediateBackend` run the task inside
the request that enqueued it. For tasks that only ever run in a dedicated
worker, use `@with_rls_context(restore=False)`: the connection is then left
empty after every task, like `RLSTask` does, so context left behind by other
code can never outlive the task.
`capture_rls_context()` returns a plain `dict` of strings, so it serializes with
any task backend.

For full control, use the context manager directly:

```python
from django_rls.tasks import task_rls_context

def run_job(payload):
    with task_rls_context(payload["rls_context"]):
        ...
```

Inline execution (Django's `ImmediateBackend`, eager Celery, tests) is safe: the
caller's context is restored when the task returns. Pass `restore=False` in
worker processes.

## API

| Name | Description |
| --- | --- |
| `django_rls.tasks.capture_rls_context()` | Snapshot of the active context (`dict[str, str]`). |
| `django_rls.tasks.task_rls_context(context, restore=True)` | Context manager: clear, apply `context`, clear, then restore the caller's context unless `restore=False`. Raises `TypeError`/`ValueError` for malformed input. |
| `django_rls.tasks.with_rls_context` | Decorator reading the context from the `_rls_context` keyword argument. `@with_rls_context(restore=False)` for worker-only tasks. |
| `django_rls.contrib.celery.RLSTask` | Celery task base class applying the context from the message header. |
| `django_rls.contrib.celery.connect_celery_signals()` | Attach the active context to published Celery tasks. `disconnect_celery_signals()` undoes it. |
