---
sidebar_position: 1
---

# Configuration

Django RLS is configured through the `DJANGO_RLS` dictionary in your Django settings.

```python
# settings.py
DJANGO_RLS = {
    "AUTO_ENABLE_RLS": True,
    "REQUIRE_CONTEXT": False,
    "ALLOW_SESSION_TENANT": False,
    "AUDIT_LOG": False,
}
```

## Settings reference

### `AUTO_ENABLE_RLS` (default: `True`)

When `True`, RLS is enabled on `RLSModel` tables after migrations via the `post_migrate` signal.

Set to `False` if you enable RLS manually (for example with `python manage.py enable_rls` in deploy scripts).

### `STRICT_MIGRATE_RLS` (default: `False`)

When `True`, failures during automatic post-migrate RLS enablement **raise** instead of being logged. Use in CI or strict deploy pipelines.

### `DEFAULT_ROLES` (default: `"public"`)

Default PostgreSQL role list for policies that do not specify `roles=` explicitly.

### `DEFAULT_PERMISSIVE` (default: `True`)

Whether new policies are permissive (`True`) or restrictive (`False`) when not specified on the policy class.

### `REQUIRE_CONTEXT` (default: `False`)

When `True`, `RLSModel` querysets require `user_id` or `tenant_id` to be set before database access. Raises `RLSContextRequiredError` if identity context is missing.

Recommended for production APIs and background workers where anonymous queries should fail closed.

### `ALLOW_SESSION_TENANT` (default: `False`)

When `True`, middleware may read `tenant_id` from `request.session`. **Disabled by default in 1.0.0** because session data is client-influenced.

Pair with `TENANT_MEMBERSHIP_VALIDATOR` when enabling.

### `TENANT_MEMBERSHIP_VALIDATOR` (default: `None`)

Dotted path to `callable(request, tenant_id) -> bool`. Called before session or `request.tenant` tenant IDs are applied.

```python
DJANGO_RLS = {
    "ALLOW_SESSION_TENANT": True,
    "TENANT_MEMBERSHIP_VALIDATOR": "myapp.security.user_belongs_to_tenant",
}
```

### `REGISTERED_CONTEXT_KEYS` (default: `[]`)

Extra session variable names (without the `rls.` prefix) cleared on connection reset and `clear_rls_context()`. `user_id` and `tenant_id` are always registered.

```python
DJANGO_RLS = {
    "REGISTERED_CONTEXT_KEYS": ["department_id", "role"],
}
```

### `RESET_CONTEXT_ON_CONNECT` (default: `True`)

Clear registered RLS session variables when Django opens a pooled database connection. Prevents stale identity from leaking across requests.

### `AUDIT_LOG` (default: `False`)

Emit structured `rls_context_set` / `rls_context_clear` log events when context changes. Useful for security audits.

### `DEBUG` (default: `False`)

Enable verbose debug logging inside django-rls.

## Production hardening example

```python
DJANGO_RLS = {
    "REQUIRE_CONTEXT": True,
    "AUDIT_LOG": True,
    "STRICT_MIGRATE_RLS": True,
    "ALLOW_SESSION_TENANT": False,
    "RESET_CONTEXT_ON_CONNECT": True,
    "REGISTERED_CONTEXT_KEYS": ["department_id"],
}
```

Run `python manage.py audit_rls` in CI before deploy to verify `ENABLE` + `FORCE ROW LEVEL SECURITY` on every `RLSModel` table.

## Database engine

Use the RLS-aware PostgreSQL backend:

```python
DATABASES = {
    "default": {
        "ENGINE": "django_rls.backends.postgresql",
        "NAME": "mydb",
        # ...
    }
}
```

SQLite and other backends do not enforce native PostgreSQL RLS.