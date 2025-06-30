"""PostgreSQL backend for Django RLS."""

from django.db.backends.postgresql import base
from django.db.backends.postgresql.schema import DatabaseSchemaEditor


class RLSDatabaseSchemaEditor(DatabaseSchemaEditor):
    """Custom schema editor that supports RLS operations."""
    
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
        self.execute(self.sql_enable_rls % {
            "table": self.quote_name(table_name)
        })
    
    def disable_rls(self, model):
        """Disable RLS on a model's table."""
        table_name = model._meta.db_table
        self.execute(self.sql_disable_rls % {
            "table": self.quote_name(table_name)
        })
    
    def force_rls(self, model):
        """Force RLS on a model's table (applies even to table owner)."""
        table_name = model._meta.db_table
        self.execute(self.sql_force_rls % {
            "table": self.quote_name(table_name)
        })
    
    def create_policy(self, model, policy):
        """Create an RLS policy."""
        table_name = model._meta.db_table
        
        # Build the SQL components
        using_clause = ""
        if hasattr(policy, 'get_using_expression'):
            expr = policy.get_using_expression()
            if expr:
                using_clause = f"USING ({expr})"
        elif hasattr(policy, 'get_sql_expression'):
            expr = policy.get_sql_expression()
            if expr:
                using_clause = f"USING ({expr})"
        
        check_clause = ""
        if hasattr(policy, 'get_check_expression'):
            expr = policy.get_check_expression()
            if expr:
                check_clause = f"WITH CHECK ({expr})"
        
        sql = self.sql_create_policy % {
            "name": self.quote_name(policy.name),
            "table": self.quote_name(table_name),
            "permissive": "PERMISSIVE" if getattr(policy, 'permissive', True) else "RESTRICTIVE",
            "operation": getattr(policy, 'operation', 'ALL'),
            "roles": getattr(policy, 'roles', 'public'),
            "using_clause": using_clause,
            "check_clause": check_clause,
        }
        
        self.execute(sql)
    
    def drop_policy(self, model, policy_name):
        """Drop an RLS policy."""
        table_name = model._meta.db_table
        self.execute(self.sql_drop_policy % {
            "name": self.quote_name(policy_name),
            "table": self.quote_name(table_name)
        })
    
    def alter_policy(self, model, policy):
        """Alter an existing RLS policy."""
        table_name = model._meta.db_table
        
        using_clause = ""
        if hasattr(policy, 'get_using_expression'):
            expr = policy.get_using_expression()
            if expr:
                using_clause = f"USING ({expr})"
        
        check_clause = ""
        if hasattr(policy, 'get_check_expression'):
            expr = policy.get_check_expression()
            if expr:
                check_clause = f"WITH CHECK ({expr})"
        
        self.execute(self.sql_alter_policy % {
            "name": self.quote_name(policy.name),
            "table": self.quote_name(table_name),
            "using_clause": using_clause,
            "check_clause": check_clause,
        })


class DatabaseWrapper(base.DatabaseWrapper):
    """Custom database wrapper that uses our RLS schema editor."""
    
    SchemaEditorClass = RLSDatabaseSchemaEditor
    
    def schema_editor(self, *args, **kwargs):
        """Return our custom schema editor."""
        return RLSDatabaseSchemaEditor(self, *args, **kwargs)