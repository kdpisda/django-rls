
# Technical Audit Report: django-rls

**Date**: 2026-01-01
**Auditor Role**: CTO / Staff Engineer
**Scope**: Security, Scalability, and Structural Integrity for Enterprise Deployment

## Executive Summary

**Recommendation**: ⛔ **DO NOT DEPLOY** in current state.

The `django-rls` library contains critical security vulnerabilities and structural defects that make it unsafe for production use, especially in a multi-tenant environment handling sensitive data. It fundamentally mismanages PostgreSQL transaction scopes and fails to clean up security contexts reliably, leading to potential data leakage between tenants.

## Critical Security Vulnerabilities

### 1. Context Leakage via Connection Pools (Critical)
**Location**: `django_rls/middleware.py`
**Issue**: The `RLSContextMiddleware` sets the RLS context (Tenant/User ID) at the start of a request and attempts to clear it at the end. However, it does not use a `try...finally` block or `process_exception`.
**Impact**: If a view raises an unhandled exception, `_clear_rls_context()` is skipped. The database connection remains tainted with the previous tenant's ID. When this connection is returned to the pool (e.g., via `django-db-geventpool`, PgBouncer, or standard Django persistent connections), the next request (potentially for a different tenant) will execute with the *previous* tenant's access rights.
**Code Evidence**:
```python
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Set RLS context before processing request
        self._set_rls_context(request)
        
        response = self.get_response(request)
        
        # Clear RLS context after processing
        # THIS IS SKIPPED ON EXCEPTION
        self._clear_rls_context()
        
        return response
```

### 2. SQL Injection in Policy Generation (High)
**Location**: `django_rls/expressions.py`
**Issue**: The library uses Python f-strings to construct SQL queries for policies instead of proper parameterization or Django's `as_sql` compiler.
**Impact**: If any part of a policy definition (e.g., a dynamic value) is influenced by user input, an attacker can inject arbitrary SQL commands.
**Code Evidence**:
```python
    def _format_value(self, value) -> str:
        if isinstance(value, str):
            # VULNERABLE: No escaping
            return f"'{value}'"

    # In _build_lookup:
    'contains': f"{field} LIKE '%' || {formatted_value} || '%'",
```

## Structural Defects

### 3. Broken RLS Context in Autocommit Mode (Critical)
**Location**: `django_rls/db/functions.py`
**Issue**: `set_rls_context` uses `set_config(..., is_local=True)`. The `is_local=True` flag scopes the setting to the *current transaction*.
**Impact**: Django runs in autocommit mode by default. Even for read-only views, each query is its own transaction.
1. `set_config` runs. Transaction commits/ends. Context is wiped.
2. `SELECT * FROM table` runs. Context is empty. RLS blocks access.
This renders the library non-functional for standard Django views unless manually wrapped in `@transaction.atomic`.

### 4. Incompatibility with Transaction Pooling (Scalability)
**Issue**: Enterprise setups with "thousands of tenants" typically require transaction pooling (e.g., PgBouncer) to manage connections.
**Impact**: PostgreSQL RLS relies on session-state variables (`app.tenant_id`). Transaction poolers reuse server connections for different clients indiscriminately. Without a mechanism to strictly reset session state (like `DISCARD ALL`) at the *proxy* level, RLS context will leak across transactions. The library provides no support for this architecture.

## Scalability Concerns

### 5. Performance Overhead
**Issue**: Every HTTP request triggers an additional database round-trip (`SELECT set_config(...)`) before the actual application logic runs.
**Impact**: For high-throughput systems, this doubles the query count for cached reads and adds significant latency.

### 6. Migration Locking
**Issue**: Enabling RLS (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) requires an `ACCESS EXCLUSIVE` lock.
**Impact**: On tables with TBs of data, this operation will lock the table for the duration, causing downtime. This is an operational constraint that must be managed carefully.

## Remediation Plan

If you must proceed with this library, the following fixes are mandatory:

1.  **Refactor Middleware**: Use `process_request` and `process_response` / `process_exception` hooks properly, or wrap the execution in `try...finally` to ensure `RESET ALL` or context clearing happens 100% of the time.
2.  **Fix Transaction Scope**: Use `is_local=False` (session scope) but strictly manage cleanup. Alternatively, force strictly atomic blocks for all RLS access.
3.  **Secure SQL Generation**: Replace string interpolation in `expressions.py` with `psycopg` safely parameterized queries or leverage `django.db.models.expressions.Func`.
4.  **Connection Pooling Strategy**: If using PgBouncer, you must configure `server_reset_query = DISCARD ALL` (standard) but verify performance impact, or use a customized reset query that clears specific RLS variables.
