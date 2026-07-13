"""Secure RLS context management.

RLS context (``rls.user_id``, ``rls.tenant_id``, etc.) is a PostgreSQL session
variable used by policies — it is **not** authentication.  This module enforces:

* **Identity immutability** — ``user_id`` and ``tenant_id`` cannot be
  overridden once set within a scope unless ``system=True``.
* **Connection hygiene** — stale context from pooled connections is cleared on
  connect and at the start of each middleware request.
* **Optional audit logging** — structured logs when context changes.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, FrozenSet, Iterator, Optional, Set

from django.db import connection

from django_rls.exceptions import RLSContextImmutableError, RLSContextRequiredError

logger = logging.getLogger(__name__)

PROTECTED_IDENTITY_KEYS: FrozenSet[str] = frozenset({"user_id", "tenant_id"})
STANDARD_CONTEXT_KEYS: FrozenSet[str] = frozenset({"user_id", "tenant_id"})

_active_context: ContextVar[Dict[str, str]] = ContextVar(
    "rls_active_context", default=None
)
_identity_locked: ContextVar[bool] = ContextVar("rls_identity_locked", default=False)
_context_source: ContextVar[Optional[str]] = ContextVar(
    "rls_context_source", default=None
)


def _get_active_context() -> Dict[str, str]:
    ctx = _active_context.get()
    if ctx is None:
        ctx = {}
        _active_context.set(ctx)
    return ctx


def get_active_rls_context() -> Dict[str, str]:
    """Return a read-only snapshot of the in-process active RLS context."""
    return dict(_get_active_context())


def get_context_source() -> Optional[str]:
    """Return how the current scope's identity was established, if known."""
    return _context_source.get()


def _audit(event: str, **fields: Any) -> None:
    from django_rls.conf import rls_config

    if rls_config.audit_log:
        logger.info("rls_%s", event, extra={"rls_event": event, **fields})


def _is_clearing(value: Any) -> bool:
    return value is None or value == ""


def _validate_identity_change(
    key: str, value: Any, *, system: bool, clearing: bool
) -> None:
    if clearing or key not in PROTECTED_IDENTITY_KEYS or system:
        return
    if _is_clearing(value):
        return

    active = _get_active_context()
    if key in active and str(active[key]) != str(value):
        raise RLSContextImmutableError(
            f"Cannot override protected RLS context key {key!r} once set. "
            f"Current value: {active[key]!r}. Use system_rls_context() for "
            "privileged context switches (background jobs, tests)."
        )


def _db_set_config(key: str, value: Any, is_local: bool = False) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, %s)",
            [f"rls.{key}", str(value), is_local],
        )


def set_rls_context(
    key: str,
    value: Any,
    is_local: bool = False,
    *,
    system: bool = False,
    source: Optional[str] = None,
) -> None:
    """Set a single RLS context value on the database connection."""
    clearing = _is_clearing(value)
    _validate_identity_change(key, value, system=system, clearing=clearing)

    _db_set_config(key, value if not clearing else "", is_local)

    active = _get_active_context()
    if clearing:
        active.pop(key, None)
        if not any(k in active for k in PROTECTED_IDENTITY_KEYS):
            _identity_locked.set(False)
        _audit("context_clear", key=key, source=source or get_context_source())
    else:
        active[key] = str(value)
        if key in PROTECTED_IDENTITY_KEYS:
            _identity_locked.set(True)
            if source:
                _context_source.set(source)
        _audit(
            "context_set",
            key=key,
            value=str(value),
            source=source or get_context_source(),
            system=system,
        )


def get_rls_context(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get current RLS context value from the database connection."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_setting(%s, true)",
            [f"rls.{key}"],
        )
        result = cursor.fetchone()
        return result[0] if result and result[0] else default


def has_rls_identity_context() -> bool:
    """Return True if user_id or tenant_id is set in the active context."""
    active = _get_active_context()
    return any(k in active and active[k] for k in PROTECTED_IDENTITY_KEYS)


def require_rls_context() -> None:
    """Raise if identity context is required by settings but not present."""
    from django_rls.conf import rls_config

    if rls_config.require_context and not has_rls_identity_context():
        raise RLSContextRequiredError(
            "RLS identity context is required but neither user_id nor tenant_id "
            "is set. Enable middleware, wrap code in rls_context(), or disable "
            "DJANGO_RLS['REQUIRE_CONTEXT'] for this environment."
        )


def get_registered_context_keys() -> Set[str]:
    """Return all context keys that should be reset on connection hygiene."""
    from django_rls.conf import rls_config

    return set(STANDARD_CONTEXT_KEYS) | set(rls_config.registered_context_keys)


def clear_rls_context(keys: Optional[Set[str]] = None) -> None:
    """Clear RLS context values from the database and in-process state."""
    keys_to_clear = keys if keys is not None else get_registered_context_keys()
    for key in keys_to_clear:
        set_rls_context(key, "", system=True, source="clear")
    if keys is None:
        _active_context.set({})
        _identity_locked.set(False)
        _context_source.set(None)


def reset_connection_rls_context() -> None:
    """Clear all registered RLS keys — call on pooled connection checkout."""
    if connection.vendor != "postgresql":
        return
    clear_rls_context()


def apply_rls_context(
    settings_map: Dict[str, Any],
    *,
    system: bool = False,
    source: str = "manual",
) -> None:
    """Apply multiple context values at once."""
    if system:
        for key in PROTECTED_IDENTITY_KEYS:
            if key in settings_map:
                set_rls_context(key, "", system=True, source=source)
    for key, value in settings_map.items():
        if value is not None and value != "":
            set_rls_context(key, value, system=system, source=source)


@contextmanager
def rls_context(
    *,
    system: bool = False,
    source: str = "manual",
    **settings: Any,
) -> Iterator[Dict[str, str]]:
    """Context manager that sets RLS variables and restores on exit."""
    if not settings:
        yield get_active_rls_context()
        return

    original_db: Dict[str, Optional[str]] = {}
    for key in settings:
        original_db[key] = get_rls_context(key)

    if system:
        for key in PROTECTED_IDENTITY_KEYS.intersection(settings.keys()):
            set_rls_context(key, "", system=True, source=source)

    try:
        apply_rls_context(settings, system=system, source=source)
        yield get_active_rls_context()
    finally:
        for key, original_value in original_db.items():
            if original_value is None:
                set_rls_context(key, "", system=True, source="restore")
            else:
                set_rls_context(key, original_value, system=True, source="restore")


@contextmanager
def system_rls_context(**settings: Any) -> Iterator[Dict[str, str]]:
    """Privileged context switch — for tests, system jobs, and migrations."""
    with rls_context(system=True, source="system", **settings) as ctx:
        yield ctx


class RLSContext:
    """Backward-compatible context manager delegating to :func:`rls_context`."""

    def __init__(self, system: bool = False, source: str = "manual", **settings: Any):
        self._settings = settings
        self._system = system
        self._source = source
        self._cm = None

    def __enter__(self) -> "RLSContext":
        self._cm = rls_context(
            system=self._system, source=self._source, **self._settings
        )
        self._cm.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._cm is not None:
            self._cm.__exit__(exc_type, exc_val, exc_tb)
