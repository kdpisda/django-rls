# Changelog

All notable changes to django-rls will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Invalid `WITH CHECK` clause on SELECT/DELETE policies** — `RLSDatabaseSchemaEditor`
  now gates `USING`/`WITH CHECK` clause generation on `policy.operation`, matching
  PostgreSQL's rules (SELECT/DELETE: `USING` only; INSERT: `WITH CHECK` only;
  UPDATE/ALL: both). Previously, `ModelPolicy` (and any policy compiled via
  `get_compiled_sql`) emitted both clauses regardless of operation, causing Postgres
  to reject `SELECT`/`DELETE` policies with "WITH CHECK cannot be applied to SELECT
  or DELETE". `BasePolicy.get_using_expression()` is likewise now omitted for
  `INSERT`-only policies. (#72)

## [1.0.0] - 2026-07-13

Major security release. **Not backward compatible** with 0.4.x for apps that relied on
session-based tenant context, identity re-assignment, or permissive `CustomPolicy`
expressions.

### Breaking Changes

- **Session `tenant_id` disabled by default** — middleware no longer reads
  `request.session["tenant_id"]` unless `DJANGO_RLS["ALLOW_SESSION_TENANT"] = True`.
- **Identity immutability** — `user_id` and `tenant_id` cannot be overridden once set
  unless `system=True` or `system_rls_context()`. Nested `RLSContext(user_id=…)` after
  middleware will raise `RLSContextImmutableError`.
- **Connection hygiene on every request** — middleware calls
  `reset_connection_rls_context()` at request start to clear stale GUCs from pooled
  connections.
- **Stricter `CustomPolicy` validation** — rejects whitespace-only expressions and
  DML keywords (`INSERT`, `UPDATE`, `DELETE`) in addition to existing DDL blocklist.
- **Context module refactor** — implementation moved to `django_rls.context`; imports
  from `django_rls.db.functions` remain supported via re-exports.

### Added

- **`django_rls.context`** — secure context management with audit logging, connection
  reset, and `require_rls_context()`.
- **`audit_rls` management command** — production readiness checks (RLS + FORCE RLS,
  `CustomPolicy` warnings).
- **`DJANGO_RLS` settings** — `REQUIRE_CONTEXT`, `STRICT_MIGRATE_RLS`, `AUDIT_LOG`,
  `ALLOW_SESSION_TENANT`, `TENANT_MEMBERSHIP_VALIDATOR`, `REGISTERED_CONTEXT_KEYS`,
  `RESET_CONTEXT_ON_CONNECT`.
- **`RLSQuerySet` enforcement** — optional identity check before DB access when
  `REQUIRE_CONTEXT=True`.
- **Security regression suite** — 109 tests in `tests/security/`.
- **New exceptions** — `RLSContextImmutableError`, `RLSContextRequiredError`,
  `TenantAccessDeniedError`.
- **Configurable policy roles**: `DJANGO_RLS["DEFAULT_ROLES"]` is now honored as the
  default `TO` role for every policy.

### Changed

- **Middleware trust boundaries** — identity comes only from authenticated `request.user`,
  `request.tenant`, user profile, or opted-in session tenant (with optional validator).
- **Policy context reads cached per-statement** — `TenantPolicy`, `UserPolicy`, and
  `ModelPolicy` wrap `current_setting()` in scalar subqueries (InitPlan pattern).
- **Absolute imports** — `django_rls.*` throughout the package.
- **`.github/SECURITY.md`** — threat model, production checklist, known limitations.

### Fixed

- **`AUTO_ENABLE_RLS=False` is now respected** — `post_migrate` early-returns when
  disabled.

### Security

- Parameterized `set_config` / `current_setting` for all context values.
- `CustomPolicy` blocklist for SQL injection and DDL/DML payloads.
- `FORCE ROW LEVEL SECURITY` always applied by `enable_rls()`.
- Middleware clears context on success and exception paths.

### Migration from 0.4.x

1. **Session tenant** — if you used `request.session["tenant_id"]`:
   ```python
   DJANGO_RLS = {"ALLOW_SESSION_TENANT": True}
   ```
2. **Re-setting identity in views/tests/workers** — use `system_rls_context()`:
   ```python
   from django_rls.context import system_rls_context

   with system_rls_context(user_id=uid, tenant_id=tid):
       MyModel.objects.filter(...)
   ```
3. **Custom context keys on pooled connections** — register them:
   ```python
   DJANGO_RLS = {"REGISTERED_CONTEXT_KEYS": ["department_id"]}
   ```
4. **Production hardening (recommended)**:
   ```python
   DJANGO_RLS = {
       "REQUIRE_CONTEXT": True,
       "AUDIT_LOG": True,
       "STRICT_MIGRATE_RLS": True,
   }
   ```
5. Run `python manage.py audit_rls` in CI before deploy.

## [0.4.1] - 2026-06-01

### Added
- Patch release prior to 1.0.0 security hardening.

## [0.2.0] - 2026-01-01

### Added
- **Django 6.0 Support**: Full compatibility with the upcoming Django 6.0 release.
- **Pythonic Policies**: Define RLS policies using standard Django `Q` objects and `ModelPolicy` class.
- **Context Processors**: Support for dynamic RLS context variables via `RLS_CONTEXT_PROCESSORS` setting.
- **Flexible User Models**: Full support for custom User models, including UUID primary keys.
- **Joined Field Support**: Automatic handling of related field lookups (e.g., `company__name`) in policies by converting them to subqueries.
- **Enterprise Features**: Examples and support for hierarchical (recursive) policies and granular ACLs.
- **Helpers**: `RLS.user_id()`, `RLS.tenant_id()`, and `RLS.context()` helpers for easy policy definition.

## [0.1.0] - 2025-01-30

### Added
- Initial release of django-rls
- Core RLSModel for Django models with PostgreSQL Row Level Security
- TenantPolicy and UserPolicy for common use cases
- Django schema editor integration for proper database operations
- Management commands: enable_rls, disable_rls
- Middleware for automatic RLS context setting
- Comprehensive test suite with >90% coverage
- Support for Django 5.0, 5.1, and 5.2 (LTS)
- Support for Python 3.10, 3.11, 3.12, and 3.13
- PostgreSQL 12+ support (tested with PostgreSQL 17)
- Documentation at https://django-rls.com

### Security
- Field name validation to prevent SQL injection
- Secure policy generation using Django's database abstraction

[unreleased]: https://github.com/kdpisda/django-rls/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/kdpisda/django-rls/compare/v0.4.1...v1.0.0
[0.4.1]: https://github.com/kdpisda/django-rls/compare/v0.2.0...v0.4.1
[0.2.0]: https://github.com/kdpisda/django-rls/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/kdpisda/django-rls/releases/tag/v0.1.0