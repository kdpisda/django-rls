"""Database functions for RLS operations."""

from django.db import connection
from django.db.models import Func, Value
from django.db.models.expressions import RawSQL


class CurrentSetting(Func):
    """PostgreSQL current_setting() function."""
    
    function = 'current_setting'
    arity = 1
    
    def __init__(self, setting_name, missing_ok=False, output_field=None):
        if missing_ok:
            super().__init__(
                Value(setting_name),
                Value('true'),
                function=self.function,
                output_field=output_field
            )
        else:
            super().__init__(
                Value(setting_name),
                function=self.function,
                output_field=output_field
            )


class SetConfig(Func):
    """PostgreSQL set_config() function."""
    
    function = 'set_config'
    arity = 3
    
    def __init__(self, setting_name, value, is_local=True):
        super().__init__(
            Value(setting_name),
            Value(str(value)),
            Value(is_local),
            function=self.function
        )


class RLSContext:
    """Context manager for RLS settings."""
    
    def __init__(self, **settings):
        self.settings = settings
        self.original_values = {}
    
    def __enter__(self):
        """Set RLS context variables."""
        with connection.cursor() as cursor:
            for key, value in self.settings.items():
                # Save original value
                cursor.execute(
                    "SELECT current_setting(%s, true)",
                    [f'rls.{key}']
                )
                result = cursor.fetchone()
                self.original_values[key] = result[0] if result else None
                
                # Set new value
                cursor.execute(
                    "SELECT set_config(%s, %s, false)",
                    [f'rls.{key}', str(value)]
                )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore original RLS context variables."""
        with connection.cursor() as cursor:
            for key, original_value in self.original_values.items():
                if original_value is not None:
                    cursor.execute(
                        "SELECT set_config(%s, %s, false)",
                        [f'rls.{key}', original_value]
                    )
                else:
                    # Clear the setting
                    cursor.execute(
                        "SELECT set_config(%s, '', false)",
                        [f'rls.{key}']
                    )


def get_rls_context(key, default=None):
    """Get current RLS context value."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_setting(%s, true)",
            [f'rls.{key}']
        )
        result = cursor.fetchone()
        return result[0] if result and result[0] else default


def set_rls_context(key, value, is_local=True):
    """Set RLS context value."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, %s)",
            [f'rls.{key}', str(value), is_local]
        )


class RLSQuerySet:
    """QuerySet mixin that provides RLS-aware methods."""
    
    def with_rls_context(self, **context):
        """Execute queryset with specific RLS context."""
        with RLSContext(**context):
            # Force evaluation within context
            return list(self)
    
    def without_rls(self):
        """Execute queryset bypassing RLS (requires superuser)."""
        # This would need to be implemented based on your security model
        # For now, it's a placeholder
        raise NotImplementedError("Bypassing RLS requires special privileges")