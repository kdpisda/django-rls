"""Expression builders for RLS policies."""

from typing import Union, List, Optional
from django.db.models import Q, F, Value
from django.db.models.expressions import Combinable, Expression
from django.db.models.sql.where import WhereNode


class RLSExpression:
    """Builder for RLS SQL expressions."""
    
    def __init__(self, expression: Union[str, Q, Expression]):
        self.expression = expression
    
    def to_sql(self) -> str:
        """Convert expression to SQL string."""
        if isinstance(self.expression, str):
            return self.expression
        
        if isinstance(self.expression, Q):
            return self._q_to_sql(self.expression)
        
        if isinstance(self.expression, Expression):
            return self._expression_to_sql(self.expression)
        
        raise ValueError(f"Unsupported expression type: {type(self.expression)}")
    
    def _q_to_sql(self, q: Q) -> str:
        """Convert Q object to SQL."""
        # This is a simplified version - in production you'd want to handle
        # all Q object features properly
        conditions = []
        
        for child in q.children:
            if isinstance(child, tuple) and len(child) == 2:
                key, value = child
                if '__' in key:
                    field, lookup = key.rsplit('__', 1)
                    conditions.append(self._build_lookup(field, lookup, value))
                else:
                    conditions.append(f"{key} = {self._format_value(value)}")
            elif isinstance(child, Q):
                conditions.append(f"({self._q_to_sql(child)})")
        
        connector = ' AND ' if q.connector == Q.AND else ' OR '
        result = connector.join(conditions)
        
        if q.negated:
            result = f"NOT ({result})"
        
        return result
    
    def _build_lookup(self, field: str, lookup: str, value) -> str:
        """Build SQL for different lookups."""
        formatted_value = self._format_value(value)
        
        lookup_map = {
            'exact': f"{field} = {formatted_value}",
            'iexact': f"LOWER({field}) = LOWER({formatted_value})",
            'contains': f"{field} LIKE '%' || {formatted_value} || '%'",
            'icontains': f"LOWER({field}) LIKE LOWER('%' || {formatted_value} || '%')",
            'gt': f"{field} > {formatted_value}",
            'gte': f"{field} >= {formatted_value}",
            'lt': f"{field} < {formatted_value}",
            'lte': f"{field} <= {formatted_value}",
            'in': f"{field} IN ({self._format_list(value)})",
            'isnull': f"{field} IS {'NULL' if value else 'NOT NULL'}",
        }
        
        return lookup_map.get(lookup, f"{field} = {formatted_value}")
    
    def _format_value(self, value) -> str:
        """Format a value for SQL."""
        if isinstance(value, str):
            # In production, use proper parameterization
            return f"'{value}'"
        elif isinstance(value, bool):
            return 'TRUE' if value else 'FALSE'
        elif value is None:
            return 'NULL'
        elif isinstance(value, (int, float)):
            return str(value)
        elif hasattr(value, 'as_sql'):
            # Handle Django expressions
            return self._expression_to_sql(value)
        else:
            return f"'{value}'"
    
    def _format_list(self, values: List) -> str:
        """Format a list of values for SQL IN clause."""
        return ', '.join(self._format_value(v) for v in values)
    
    def _expression_to_sql(self, expr: Expression) -> str:
        """Convert Django expression to SQL."""
        # This is simplified - in production you'd use the proper compiler
        if isinstance(expr, F):
            return str(expr.name)
        elif isinstance(expr, Value):
            return self._format_value(expr.value)
        else:
            # For other expressions, you'd need to use Django's SQL compiler
            return str(expr)


class CurrentUser:
    """Expression for current user ID from RLS context."""
    
    def __str__(self):
        return "current_setting('rls.user_id')::integer"
    
    def as_sql(self):
        return str(self)


class CurrentTenant:
    """Expression for current tenant ID from RLS context."""
    
    def __str__(self):
        return "current_setting('rls.tenant_id')::integer"
    
    def as_sql(self):
        return str(self)


class RLSQuery:
    """Helper for building complex RLS queries."""
    
    @staticmethod
    def user_owns(field: str = 'user_id') -> str:
        """Check if current user owns the row."""
        return f"{field} = {CurrentUser()}"
    
    @staticmethod
    def tenant_owns(field: str = 'tenant_id') -> str:
        """Check if current tenant owns the row."""
        return f"{field} = {CurrentTenant()}"
    
    @staticmethod
    def user_in_group(group_table: str, user_field: str = 'user_id', 
                      group_field: str = 'group_id') -> str:
        """Check if user is in a group that has access."""
        return f"""
        EXISTS (
            SELECT 1 FROM {group_table}
            WHERE {group_table}.{user_field} = {CurrentUser()}
            AND {group_table}.{group_field} = {group_field}
        )
        """
    
    @staticmethod
    def has_permission(permission: str, permission_table: str = 'auth_user_user_permissions') -> str:
        """Check if user has a specific permission."""
        return f"""
        EXISTS (
            SELECT 1 FROM {permission_table} p
            JOIN auth_permission perm ON p.permission_id = perm.id
            WHERE p.user_id = {CurrentUser()}
            AND perm.codename = '{permission}'
        )
        """