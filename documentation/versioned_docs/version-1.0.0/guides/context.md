---
sidebar_position: 2
---

# RLS Context

RLS context (`rls.user_id`, `rls.tenant_id`, and custom keys) are PostgreSQL session variables read by your policies. They are **not** authentication — they tell PostgreSQL which identity to filter for on this connection.

In **1.0.0**, context management lives in `django_rls.context`. Imports from `django_rls.db.functions` still work via re-exports.

## Middleware (HTTP requests)

`RLSContextMiddleware` sets identity from trusted request attributes only:

- `request.user.id` (authenticated users)
- `request.tenant.id`
- `request.user.profile.tenant_id` (if present)
- `request.session["tenant_id"]` — **only when** `ALLOW_SESSION_TENANT=True`

Headers, query strings, and JSON bodies **cannot** inject context.

## Setting context manually

```python
from django_rls.context import set_rls_context, get_rls_context

set_rls_context("user_id", 42, system=True)
set_rls_context("tenant_id", 7, system=True)

assert get_rls_context("user_id") == "42"
```

Use `system=True` when establishing identity from a trusted source (middleware, workers, tests).

## Identity immutability (1.0.0)

Once `user_id` or `tenant_id` is set, they cannot be overwritten unless you use a **privileged** scope:

```python
from django_rls.context import set_rls_context, system_rls_context
from django_rls.exceptions import RLSContextImmutableError

set_rls_context("user_id", 1, system=True)
set_rls_context("user_id", 2)  # raises RLSContextImmutableError

with system_rls_context(user_id=99):
    # privileged switch for workers, admin tasks, tests
    ...
```

## Context managers

### `system_rls_context()` — workers, tests, migrations

```python
from django_rls.context import system_rls_context

def process_invoice(invoice_id, actor_user_id, tenant_id):
    with system_rls_context(user_id=actor_user_id, tenant_id=tenant_id):
        return Invoice.objects.get(pk=invoice_id)
```

### `rls_context()` — restore previous values on exit

```python
from django_rls.context import rls_context

with rls_context(system=True, user_id=10, department_id="sales"):
    Document.objects.filter(...)
# previous session values restored
```

## Background jobs (Celery, async workers)

HTTP middleware does **not** run in workers. You must:

1. Derive `user_id` / `tenant_id` from the job payload or database — never trust raw task arguments alone.
2. Wrap work in `system_rls_context()`.
3. Rely on connection hygiene (`RESET_CONTEXT_ON_CONNECT`) so pooled connections do not retain stale identity.

```python
from django_rls.context import system_rls_context, reset_connection_rls_context

@shared_task
def export_tenant_data(tenant_id, requested_by_id):
    reset_connection_rls_context()
    with system_rls_context(user_id=requested_by_id, tenant_id=tenant_id):
        return list(Report.objects.values())
```

## Clearing context

```python
from django_rls.context import clear_rls_context

clear_rls_context()  # clears all registered keys in DB + in-process state
```

Middleware clears context in a `finally` block after every request, including when views raise exceptions.

## Requiring identity

When `REQUIRE_CONTEXT=True`:

```python
DJANGO_RLS = {"REQUIRE_CONTEXT": True}
```

```python
from django_rls.exceptions import RLSContextRequiredError

Document.objects.count()  # raises RLSContextRequiredError without identity

with system_rls_context(user_id=1):
    Document.objects.count()  # OK
```