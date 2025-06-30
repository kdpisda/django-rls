"""RLS Policy classes."""

import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from django.db.models import Q, F
from django.db.models.sql.where import WhereNode

from .exceptions import PolicyError


class BasePolicy(ABC):
    """Base class for all RLS policies."""
    
    # Policy operations
    ALL = 'ALL'
    SELECT = 'SELECT'
    INSERT = 'INSERT'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    
    # Regex pattern to validate field names (alphanumeric + underscore)
    FIELD_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    
    def __init__(self, name: str, operation: str = ALL, permissive: bool = True, 
                 roles: str = 'public', **kwargs):
        self.name = name
        self.operation = operation
        self.permissive = permissive
        self.roles = roles
        self.options = kwargs
        self.validate()
    
    def validate(self) -> None:
        """Validate policy configuration."""
        if not self.name:
            raise PolicyError("Policy name is required")
        
        valid_operations = [self.ALL, self.SELECT, self.INSERT, self.UPDATE, self.DELETE]
        if self.operation not in valid_operations:
            raise PolicyError(f"Invalid operation: {self.operation}")
    
    def validate_field_name(self, field_name: str) -> None:
        """Validate that a field name is safe for SQL."""
        if not self.FIELD_NAME_PATTERN.match(field_name):
            raise PolicyError(
                f"Invalid field name '{field_name}'. Field names must contain only "
                f"letters, numbers, and underscores, and must start with a letter or underscore."
            )
    
    @abstractmethod
    def get_sql_expression(self) -> str:
        """Return the SQL expression for this policy."""
        pass
    
    def get_using_expression(self) -> Optional[str]:
        """Return the USING clause expression (for SELECT/DELETE)."""
        return self.get_sql_expression()
    
    def get_check_expression(self) -> Optional[str]:
        """Return the WITH CHECK clause expression (for INSERT/UPDATE)."""
        # By default, use the same expression as USING
        if self.operation in [self.INSERT, self.UPDATE, self.ALL]:
            return self.get_sql_expression()
        return None


class TenantPolicy(BasePolicy):
    """Policy for tenant-based RLS."""
    
    def __init__(self, name: str, tenant_field: str, **kwargs):
        self.tenant_field = tenant_field
        super().__init__(name, **kwargs)
    
    def validate(self) -> None:
        super().validate()
        if not self.tenant_field:
            raise PolicyError("tenant_field is required for TenantPolicy")
        self.validate_field_name(self.tenant_field)
    
    def get_sql_expression(self) -> str:
        """Generate SQL expression for tenant-based filtering."""
        return f"{self.tenant_field}_id = current_setting('rls.tenant_id')::integer"


class UserPolicy(BasePolicy):
    """Policy for user-based RLS."""
    
    def __init__(self, name: str, user_field: str = 'user', **kwargs):
        self.user_field = user_field
        super().__init__(name, **kwargs)
    
    def validate(self) -> None:
        super().validate()
        if not self.user_field:
            raise PolicyError("user_field is required for UserPolicy")
        self.validate_field_name(self.user_field)
    
    def get_sql_expression(self) -> str:
        """Generate SQL expression for user-based filtering."""
        return f"{self.user_field}_id = current_setting('rls.user_id')::integer"


class CustomPolicy(BasePolicy):
    """Policy with custom SQL expression."""
    
    def __init__(self, name: str, expression: str, **kwargs):
        self.expression = expression
        super().__init__(name, **kwargs)
    
    def validate(self) -> None:
        super().validate()
        if not self.expression:
            raise PolicyError("expression is required for CustomPolicy")
    
    def get_sql_expression(self) -> str:
        """Return the custom SQL expression."""
        return self.expression