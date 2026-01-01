"""RLS Policy classes."""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model
from django.db.models import CharField, Func, IntegerField, Q, Value
from django.db.models.sql import Query

from .exceptions import PolicyError


class BasePolicy(ABC):
    """Base class for all RLS policies."""

    # Policy operations
    ALL = "ALL"
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

    # Regex pattern to validate field names (alphanumeric + underscore)
    FIELD_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    def __init__(
        self,
        name: str,
        operation: str = ALL,
        permissive: bool = True,
        roles: str = "public",
        **kwargs,
    ):
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

        valid_operations = [
            self.ALL,
            self.SELECT,
            self.INSERT,
            self.UPDATE,
            self.DELETE,
        ]
        if self.operation not in valid_operations:
            raise PolicyError(f"Invalid operation: {self.operation}")

    def validate_field_name(self, field_name: str) -> None:
        """Validate that a field name is safe for SQL."""
        if not self.FIELD_NAME_PATTERN.match(field_name):
            raise PolicyError(
                f"Invalid field name '{field_name}'. Field names must contain only "
                "letters, numbers, and underscores, and must start with a letter "
                "or underscore."
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
        return (
            f"{self.tenant_field}_id = "
            f"NULLIF(current_setting('rls.tenant_id', true), '') "
            ":: integer"  # noqa: E231
        )


class UserPolicy(BasePolicy):
    """Policy for user-based RLS."""

    def __init__(self, name: str, user_field: str = "user", **kwargs):
        self.user_field = user_field
        super().__init__(name, **kwargs)

    def validate(self) -> None:
        super().validate()
        if not self.user_field:
            raise PolicyError("user_field is required for UserPolicy")
        self.validate_field_name(self.user_field)

    def get_sql_expression(self) -> str:
        """Generate SQL expression for user-based filtering."""
        return (
            f"{self.user_field}_id = "
            f"NULLIF(current_setting('rls.user_id', true), '') :: integer"  # noqa: E231
        )


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


class CurrentContext(Func):
    """
    Expression representing a Postgres current_setting call.
    Default casts to integer (ID-based RLS), but can be overridden.
    """

    function = "current_setting"
    # Base template, we append cast if needed or use output_field handling
    template = "NULLIF(current_setting(%(expressions)s, true), '')"

    def __init__(self, expression, output_field=None, **extra):
        if output_field is None:
            # Default to integer for backward compatibility and common usecase
            output_field = IntegerField()
        super().__init__(expression, output_field=output_field, **extra)

    def as_postgresql(self, compiler, connection, **extra_context):
        # We handle casting explicitly in SQL for clarity
        sql, params = super().as_sql(compiler, connection, **extra_context)
        if isinstance(self.output_field, IntegerField):
            return f"({sql}) :: integer", params  # noqa: E231

        from django.db.models import UUIDField

        if isinstance(self.output_field, UUIDField):
            return f"({sql}) :: uuid", params  # noqa: E231

        # Text doesn't need implicit cast usually, but safe to leave as string
        return sql, params


class UserContext(CurrentContext):
    """
    Specialized context for User ID that resolves the User model's PK type lazily.
    """

    def __init__(self, **extra):
        # We don't set output_field here, we wait for resolve_expression
        super().__init__(Value("rls.user_id"), output_field=None, **extra)

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        if self.output_field is None:
            try:
                user_model = get_user_model()
                self.output_field = user_model._meta.pk
            except Exception:
                # Fallback if apps not ready (unlikely during query execution)
                self.output_field = IntegerField()

        return super().resolve_expression(
            query, allow_joins, reuse, summarize, for_save
        )


class RLS:
    """Helper to access RLS context variables in Q objects."""

    @staticmethod
    def user_id():
        """
        Returns a context expression for the current user's ID.
        Automatically detects the User model's primary key type (Integer, UUID, etc).
        """
        return UserContext()

    @staticmethod
    def tenant_id():
        return CurrentContext(Value("rls.tenant_id"), output_field=IntegerField())

    @staticmethod
    def context(name: str, output_field=None):
        """
        Generic context accessor.
        Example: RLS.context('user_email', CharField())
        """
        if output_field is None:
            output_field = CharField()
        return CurrentContext(Value(f"rls.{name}"), output_field=output_field)


class ModelPolicy(BasePolicy):
    """
    Policy defined using Django Q objects and model fields.
    Avoids raw SQL strings.
    """

    def __init__(
        self, name: str, filters: Q, annotations: Dict[str, Any] = None, **kwargs
    ):
        self.filters = filters
        self.annotations = annotations or {}
        super().__init__(name, **kwargs)

    def validate(self) -> None:
        super().validate()
        if not isinstance(self.filters, Q):
            raise PolicyError("filters must be a Django Q object")

    def get_sql_expression(self) -> str:
        raise NotImplementedError(
            "ModelPolicy requires the model class to compile SQL. "
            "Use get_compiled_sql(model)."
        )

    def get_compiled_sql(self, model) -> str:
        """
        Compile Q object using the provided model.
        """

        # Rewrite filters to avoid JOINs (Issue #14)
        rewritten_filters = self._rewrite_filters(self.filters, model)

        query = Query(model)

        # Add annotations if any
        for alias, expr in self.annotations.items():
            query.add_annotation(expr, alias)

        query.add_q(rewritten_filters)
        compiler = query.get_compiler("default")  # Use default connection compiler
        sql, params = compiler.compile(query.where)

        # Safe parameter interpolation for DDL
        def quote_val(p):
            if isinstance(p, str):
                return f"'{p}'"
            if p is None:
                return "NULL"
            return str(p)

        formatted_sql = sql % tuple(quote_val(p) for p in params)

        # Escape percentage signs for double-interpolation
        # (Python % formatting + Psycopg). We need '%%' to reach psycopg.
        # create_policy uses % formatting, so we need '%%%%' to produce '%%'.
        return formatted_sql.replace("%", "%%%%")

    def _rewrite_filters(self, q_obj: Q, model) -> Q:
        """
        Recursively rewrite Q object to convert related field lookups (JOINs)
        into subqueries (IN clauses), as Postgres ROW LEVEL SECURITY policies
        cannot contain JOINs in the USING clause.
        """
        new_children = []
        for child in q_obj.children:
            if isinstance(child, Q):
                new_children.append(self._rewrite_filters(child, model))
            elif isinstance(child, tuple):
                lookup, value = child
                # Check if lookup implies a join (contains '__')
                # But filter out standard lookups like 'field__in', 'field__gt'
                # We need to see if the first part is a Relation field.

                # Split at first '__'
                parts = lookup.split("__", 1)
                if len(parts) > 1:
                    field_name = parts[0]
                    rest = parts[1]

                    try:
                        field = model._meta.get_field(field_name)
                    except Exception:
                        # Field not found or other error, assume not a relation or
                        # let it fail naturally
                        field = None

                    if field and field.is_relation and field.many_to_one:
                        # It is a ForeignKey (ManyToOne)

                        # Generate Subquery:
                        # related_id IN (SELECT id FROM RelatedModel WHERE rest=value)
                        related_model = field.related_model

                        # Recursive rewrite?
                        # If 'rest' contains more joins, Django ORM handles them inside
                        # the subquery fine!
                        # We only need to avoid joins on the MAIN table (the policy
                        # target).

                        subquery = related_model.objects.filter(**{rest: value}).values(
                            "pk"
                        )

                        # Replace 'company__name' with 'company_id__in'
                        new_lookup = f"{field.attname}__in"
                        new_children.append((new_lookup, subquery))
                        continue

                # If not converted, keep properly
                new_children.append(child)
            else:
                # Other types (expressions etc)
                new_children.append(child)

        # Return new Q with same connector
        new_q = Q()
        new_q.children = new_children
        new_q.connector = q_obj.connector
        new_q.negated = q_obj.negated
        return new_q
