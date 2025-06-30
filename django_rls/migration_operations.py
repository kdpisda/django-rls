"""Django migration operations for RLS."""

from django.db import router
from django.db.migrations.operations.base import Operation


class RLSOperation(Operation):
    """Base class for RLS migration operations."""
    
    def __init__(self, model_name):
        self.model_name = model_name
    
    def state_forwards(self, app_label, state):
        """RLS operations don't change model state."""
        pass
    
    def describe(self):
        """Describe this operation."""
        return f"{self.__class__.__name__} for {self.model_name}"
    
    def get_model(self, app_label, schema_editor):
        """Get the model class."""
        return router.db_for_write(
            schema_editor.connection.introspection.get_table_list(schema_editor.connection.cursor())
        )


class EnableRLS(RLSOperation):
    """Migration operation to enable RLS on a model."""
    
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """Enable RLS on the model's table."""
        if hasattr(schema_editor, 'enable_rls'):
            model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.enable_rls(model)
    
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """Disable RLS on the model's table."""
        if hasattr(schema_editor, 'disable_rls'):
            model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.disable_rls(model)
    
    def describe(self):
        return f"Enable RLS on {self.model_name}"


class DisableRLS(RLSOperation):
    """Migration operation to disable RLS on a model."""
    
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """Disable RLS on the model's table."""
        if hasattr(schema_editor, 'disable_rls'):
            model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.disable_rls(model)
    
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """Enable RLS on the model's table."""
        if hasattr(schema_editor, 'enable_rls'):
            model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.enable_rls(model)
    
    def describe(self):
        return f"Disable RLS on {self.model_name}"


class CreatePolicy(Operation):
    """Migration operation to create an RLS policy."""
    
    def __init__(self, model_name, policy):
        self.model_name = model_name
        self.policy = policy
    
    def state_forwards(self, app_label, state):
        """Policies don't change model state."""
        pass
    
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """Create the RLS policy."""
        if hasattr(schema_editor, 'create_policy'):
            model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.create_policy(model, self.policy)
    
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """Drop the RLS policy."""
        if hasattr(schema_editor, 'drop_policy'):
            model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.drop_policy(model, self.policy.name)
    
    def describe(self):
        return f"Create RLS policy {self.policy.name} on {self.model_name}"
    
    def deconstruct(self):
        """Deconstruct for migrations."""
        return (
            self.__class__.__name__,
            [self.model_name, self.policy],
            {}
        )


class DropPolicy(Operation):
    """Migration operation to drop an RLS policy."""
    
    def __init__(self, model_name, policy_name):
        self.model_name = model_name
        self.policy_name = policy_name
    
    def state_forwards(self, app_label, state):
        """Policies don't change model state."""
        pass
    
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """Drop the RLS policy."""
        if hasattr(schema_editor, 'drop_policy'):
            model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.drop_policy(model, self.policy_name)
    
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """Recreate the RLS policy (requires policy definition)."""
        # This would need the original policy definition to recreate
        pass
    
    def describe(self):
        return f"Drop RLS policy {self.policy_name} on {self.model_name}"
    
    def deconstruct(self):
        """Deconstruct for migrations."""
        return (
            self.__class__.__name__,
            [self.model_name, self.policy_name],
            {}
        )


class AlterPolicy(Operation):
    """Migration operation to alter an RLS policy."""
    
    def __init__(self, model_name, policy):
        self.model_name = model_name
        self.policy = policy
    
    def state_forwards(self, app_label, state):
        """Policies don't change model state."""
        pass
    
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """Alter the RLS policy."""
        if hasattr(schema_editor, 'alter_policy'):
            model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.alter_policy(model, self.policy)
    
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """Reversing an alter is complex and would need the original policy."""
        pass
    
    def describe(self):
        return f"Alter RLS policy {self.policy.name} on {self.model_name}"
    
    def deconstruct(self):
        """Deconstruct for migrations."""
        return (
            self.__class__.__name__,
            [self.model_name, self.policy],
            {}
        )