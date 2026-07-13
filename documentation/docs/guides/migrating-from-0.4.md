---
sidebar_position: 7
---

# Migrating from 0.4.x

django-rls **1.0.0** is a major security release. It is **not** drop-in compatible if your app relied on session-based tenant context, identity re-assignment, or permissive `CustomPolicy` expressions.

See the [0.4 documentation](/docs/0.4/intro) if you need to stay on the previous release line.

## Breaking changes summary

| Area | 0.4.x | 1.0.0 |
|------|-------|-------|
| Session `tenant_id` | Used by default | **Off** unless `ALLOW_SESSION_TENANT=True` |
| Override `user_id` / `tenant_id` | Allowed | **Immutable** unless `system_rls_context()` |
| Connection pooling | Context could persist | **Reset** on connect + each request |
| `CustomPolicy` validation | DDL blocklist | Also rejects whitespace-only + DML keywords |
| Context implementation | `db.functions` | `django_rls.context` (re-exports remain) |

## Step-by-step migration

### 1. Session-based tenant ID

If you used `request.session["tenant_id"]`:

```python
DJANGO_RLS = {
    "ALLOW_SESSION_TENANT": True,
    "TENANT_MEMBERSHIP_VALIDATOR": "myapp.auth.user_can_access_tenant",
}
```

Without the validator, any session value could select a tenant. Add membership checks before enabling in production.

### 2. Re-setting identity in views, tests, or workers

**Before (0.4.x):**

```python
set_rls_context("user_id", other_user_id)
```

**After (1.0.0):**

```python
from django_rls.context import system_rls_context

with system_rls_context(user_id=other_user_id):
    MyModel.objects.filter(...)
```

Update tests that call `set_rls_context` multiple times for different users.

### 3. Custom context keys on pooled connections

Register keys that must be cleared when connections are reused:

```python
DJANGO_RLS = {
    "REGISTERED_CONTEXT_KEYS": ["department_id", "role"],
}
```

### 4. CustomPolicy expressions

Review any `CustomPolicy` using DML keywords (`INSERT`, `UPDATE`, `DELETE`) or blank expressions — they are rejected at construction time in 1.0.0.

### 5. Production hardening (recommended)

```python
DJANGO_RLS = {
    "REQUIRE_CONTEXT": True,
    "AUDIT_LOG": True,
    "STRICT_MIGRATE_RLS": True,
}
```

Add to CI:

```bash
python manage.py audit_rls
```

### 6. Import paths

Prefer:

```python
from django_rls.context import set_rls_context, system_rls_context
```

Existing imports still work:

```python
from django_rls.db.functions import set_rls_context  # re-export
```

## Upgrade command

```bash
pip install "django-rls>=1.0.0,<2.0.0"
```

Run your test suite against **real PostgreSQL** (`make test` locally). SQLite does not exercise RLS.

## Need the old behavior?

- Stay on `django-rls==0.4.1` and use the [0.4 docs](/docs/0.4/intro).
- Or opt in selectively with `ALLOW_SESSION_TENANT` and `system_rls_context()` rather than downgrading.