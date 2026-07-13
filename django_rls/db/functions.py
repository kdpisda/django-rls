"""Database functions for RLS operations."""

from django.db import connection
from django.db.models import Func, Value

# Re-export secure context API for backward compatibility.
from django_rls.context import (  # noqa: F401
    RLSContext,
    apply_rls_context,
    clear_rls_context,
    get_active_rls_context,
    get_rls_context,
    has_rls_identity_context,
    require_rls_context,
    reset_connection_rls_context,
    rls_context,
    set_rls_context,
    system_rls_context,
)


class CurrentSetting(Func):
    """PostgreSQL current_setting() function."""

    function = "current_setting"
    arity = 1

    def __init__(self, setting_name, missing_ok=False, output_field=None):
        if missing_ok:
            super().__init__(
                Value(setting_name),
                Value("true"),
                function=self.function,
                output_field=output_field,
            )
        else:
            super().__init__(
                Value(setting_name),
                function=self.function,
                output_field=output_field,
            )


class SetConfig(Func):
    """PostgreSQL set_config() function."""

    function = "set_config"
    arity = 3

    def __init__(self, setting_name, value, is_local=True):
        super().__init__(
            Value(setting_name),
            Value(str(value)),
            Value(is_local),
            function=self.function,
        )


class RLSQuerySet:
    """QuerySet mixin that provides RLS-aware methods."""

    def with_rls_context(self, **context):
        """Execute queryset with specific RLS context."""
        with RLSContext(**context):
            return list(self)

    def without_rls(self):
        """Execute queryset bypassing RLS (requires superuser)."""
        raise NotImplementedError("Bypassing RLS requires special privileges")
