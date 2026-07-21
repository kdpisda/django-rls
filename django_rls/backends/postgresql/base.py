"""PostgreSQL backend for Django RLS."""

from django.db.backends.postgresql import base
from django.db.backends.postgresql.schema import DatabaseSchemaEditor


class RLSDatabaseSchemaEditor(DatabaseSchemaEditor):
    """Custom schema editor that supports RLS operations."""

    # PostgreSQL restricts which clauses a CREATE/ALTER POLICY may carry,
    # based on the policy's FOR <operation>:
    #   SELECT / DELETE -> USING only
    #   INSERT           -> WITH CHECK only
    #   UPDATE / ALL     -> both USING and WITH CHECK
    # An operation value we don't recognize (e.g. a test double that never
    # set `.operation`) is treated permissively, generating both clauses,
    # matching the previous unconditional behavior.
    USING_OPERATIONS = {"SELECT", "UPDATE", "DELETE", "ALL"}
    CHECK_OPERATIONS = {"INSERT", "UPDATE", "ALL"}
    KNOWN_OPERATIONS = USING_OPERATIONS | CHECK_OPERATIONS

    sql_enable_rls = "ALTER TABLE %(table)s ENABLE ROW LEVEL SECURITY"
    sql_disable_rls = "ALTER TABLE %(table)s DISABLE ROW LEVEL SECURITY"
    sql_force_rls = "ALTER TABLE %(table)s FORCE ROW LEVEL SECURITY"

    sql_create_policy = """
        CREATE POLICY %(name)s ON %(table)s
        AS %(permissive)s
        FOR %(operation)s
        TO %(roles)s
        %(using_clause)s
        %(check_clause)s
    """

    sql_drop_policy = "DROP POLICY IF EXISTS %(name)s ON %(table)s"

    sql_alter_policy = """
        ALTER POLICY %(name)s ON %(table)s
        %(using_clause)s
        %(check_clause)s
    """

    def enable_rls(self, model):
        """Enable RLS on a model's table."""
        table_name = model._meta.db_table
        self.execute(self.sql_enable_rls % {"table": self.quote_name(table_name)})

    def disable_rls(self, model):
        """Disable RLS on a model's table."""
        table_name = model._meta.db_table
        self.execute(self.sql_disable_rls % {"table": self.quote_name(table_name)})

    def force_rls(self, model):
        """Force RLS on a model's table (applies even to table owner)."""
        table_name = model._meta.db_table
        self.execute(self.sql_force_rls % {"table": self.quote_name(table_name)})

    def _build_clauses(self, policy, model):
        """Build the USING and WITH CHECK clauses for a policy.

        Clause generation is gated on ``policy.operation`` here — the single
        place both ``create_policy`` and ``alter_policy`` go through — so an
        operation that PostgreSQL doesn't allow a given clause for (e.g.
        WITH CHECK on a SELECT policy) never reaches the generated DDL.
        See issue #72.
        """
        operation = getattr(policy, "operation", None)
        wants_using = operation not in self.KNOWN_OPERATIONS or operation in self.USING_OPERATIONS
        wants_check = operation not in self.KNOWN_OPERATIONS or operation in self.CHECK_OPERATIONS

        using_clause = ""
        if wants_using:
            expr = None
            # Model-aware compilation (ModelPolicy) takes priority.
            if hasattr(policy, "get_compiled_sql"):
                expr = policy.get_compiled_sql(model)
            elif hasattr(policy, "get_using_expression"):
                expr = policy.get_using_expression()
            elif hasattr(policy, "get_sql_expression"):
                expr = policy.get_sql_expression()
            if expr:
                using_clause = f"USING ({expr})"

        check_clause = ""
        if wants_check:
            expr = None
            # ModelPolicy uses the same compiled filter for the check clause.
            if hasattr(policy, "get_compiled_sql"):
                expr = policy.get_compiled_sql(model)
            elif hasattr(policy, "get_check_expression"):
                expr = policy.get_check_expression()
            if expr:
                check_clause = f"WITH CHECK ({expr})"

        return using_clause, check_clause

    def create_policy(self, model, policy):
        """Create an RLS policy."""
        table_name = model._meta.db_table

        using_clause, check_clause = self._build_clauses(policy, model)

        sql = self.sql_create_policy % {
            "name": self.quote_name(policy.name),
            "table": self.quote_name(table_name),
            "permissive": "PERMISSIVE"
            if getattr(policy, "permissive", True)
            else "RESTRICTIVE",
            "operation": getattr(policy, "operation", "ALL"),
            "roles": getattr(policy, "roles", "public"),
            "using_clause": using_clause,
            "check_clause": check_clause,
        }

        self.execute(sql)

    def drop_policy(self, model, policy_name):
        """Drop an RLS policy."""
        table_name = model._meta.db_table
        self.execute(
            self.sql_drop_policy
            % {
                "name": self.quote_name(policy_name),
                "table": self.quote_name(table_name),
            }
        )

    def alter_policy(self, model, policy):
        """Alter an existing RLS policy."""
        table_name = model._meta.db_table

        using_clause, check_clause = self._build_clauses(policy, model)

        self.execute(
            self.sql_alter_policy
            % {
                "name": self.quote_name(policy.name),
                "table": self.quote_name(table_name),
                "using_clause": using_clause,
                "check_clause": check_clause,
            }
        )


class DatabaseWrapper(base.DatabaseWrapper):
    """Custom database wrapper that uses our RLS schema editor."""

    SchemaEditorClass = RLSDatabaseSchemaEditor

    def schema_editor(self, *args, **kwargs):
        """Return our custom schema editor."""
        return RLSDatabaseSchemaEditor(self, *args, **kwargs)
