# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| < 0.4   | :x:                |

## Reporting a Vulnerability

We take the security of Django RLS seriously.

1. **Do NOT** open a public GitHub issue for critical vulnerabilities.
2. Email **security@django-rls.org** (or contact maintainers directly) with:
   - Description and reproduction steps
   - Impact assessment
   - Affected versions
3. **Response timeline:** initial reply within 48 hours; fix timeline depends on severity.

## Threat Model

### What RLS context is

`rls.user_id`, `rls.tenant_id`, and custom `rls.*` keys are **PostgreSQL session variables** read by RLS policies. They are **not authentication**. Middleware sets them from Django's authenticated `request.user`; any application code with DB access can also call `set_config`.

### Trust boundaries

| Source | Trust level |
|--------|-------------|
| `RLSContextMiddleware` (from `request.user`) | Trusted identity for HTTP requests |
| `rls_context()` / `system_rls_context()` | Application code — must not use user-supplied values |
| Celery task arguments / headers (future) | Untrusted unless signed and capture-only |
| `CustomPolicy` raw SQL | Developer-supplied — validated but prefer `ModelPolicy` |

### What the library enforces

- **Identity immutability:** `user_id` and `tenant_id` cannot be overridden once set unless `system=True` (`system_rls_context()`).
- **Session tenant disabled by default:** `tenant_id` from `request.session` requires `ALLOW_SESSION_TENANT=True` plus optional `TENANT_MEMBERSHIP_VALIDATOR`.
- **Connection hygiene:** RLS GUCs cleared on DB connect and at the start of each middleware request.
- **CustomPolicy validation:** Rejects obvious SQL injection / DDL tokens.
- **FORCE RLS:** `enable_rls()` always applies `FORCE ROW LEVEL SECURITY`.
- **Optional strict mode:** `REQUIRE_CONTEXT=True` raises if identity context is missing before RLS model queries.

### What you must configure

- App DB user must **not** have `BYPASSRLS` or own tables without `FORCE RLS`.
- Run `python manage.py audit_rls` in CI before deploy.
- Use `DJANGO_RLS['DEFAULT_ROLES']` to scope policies (avoid `public` in production if possible).
- Register custom context keys in `REGISTERED_CONTEXT_KEYS` for connection reset.
- Enable `AUDIT_LOG=True` for context change logging in regulated environments.

## Security Checklist (Production)

- [ ] `python manage.py audit_rls` passes (RLS + FORCE on all sensitive tables)
- [ ] App DB role has least privilege (no `SUPERUSER`, no `BYPASSRLS`)
- [ ] `ALLOW_SESSION_TENANT` is `False` (default) or paired with `TENANT_MEMBERSHIP_VALIDATOR`
- [ ] `REQUIRE_CONTEXT=True` in production
- [ ] `AUDIT_LOG=True` with centralized log collection
- [ ] SSL enabled for database connections
- [ ] Prefer `ModelPolicy` over `CustomPolicy`
- [ ] Background tasks use `system_rls_context()` with server-derived IDs only
- [ ] Security tests pass: `poetry run pytest tests/security/ tests/test_security.py`

## Known Limitations

- **Postgres side channels:** PK uniqueness errors can leak row existence (documented; use UUIDs where needed).
- **RLS ≠ app auth:** Django superuser does not bypass RLS; do not rely on RLS alone for admin bypass logic.
- **Permissive policies:** Default is permissive (OR semantics). Use restrictive policies for deny-by-default patterns.

## References

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [OWASP Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)
