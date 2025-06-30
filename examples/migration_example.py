"""Example of using RLS with Django migrations."""

from django.db import migrations
from django_rls.migration_operations import EnableRLS, CreatePolicy
from django_rls.policies import UserPolicy, TenantPolicy


class Migration(migrations.Migration):
    """Example migration showing how to enable RLS."""
    
    dependencies = [
        ('myapp', '0001_initial'),
    ]
    
    operations = [
        # Enable RLS on the Document model
        EnableRLS('Document'),
        
        # Create a user-based policy
        CreatePolicy(
            'Document',
            UserPolicy('document_owner_policy', user_field='owner')
        ),
        
        # Enable RLS on the Project model  
        EnableRLS('Project'),
        
        # Create a tenant-based policy
        CreatePolicy(
            'Project',
            TenantPolicy('project_tenant_policy', tenant_field='organization')
        ),
    ]


# You can also use RunPython for more complex scenarios
def enable_rls_for_all_models(apps, schema_editor):
    """Enable RLS for all models that inherit from RLSModel."""
    from django_rls.models import RLSModel
    
    for model in apps.get_models():
        if issubclass(model, RLSModel) and hasattr(model, '_rls_policies'):
            # Use the schema editor to enable RLS
            if hasattr(schema_editor, 'enable_rls'):
                schema_editor.enable_rls(model)
                
                # Create all policies
                for policy in model._rls_policies:
                    schema_editor.create_policy(model, policy)


def disable_rls_for_all_models(apps, schema_editor):
    """Disable RLS for all models."""
    from django_rls.models import RLSModel
    
    for model in apps.get_models():
        if issubclass(model, RLSModel) and hasattr(model, '_rls_policies'):
            if hasattr(schema_editor, 'disable_rls'):
                # Drop all policies
                for policy in model._rls_policies:
                    schema_editor.drop_policy(model, policy.name)
                
                # Disable RLS
                schema_editor.disable_rls(model)


class AutoRLSMigration(migrations.Migration):
    """Migration that automatically enables RLS for all RLSModel subclasses."""
    
    dependencies = [
        ('myapp', '0002_create_models'),
    ]
    
    operations = [
        migrations.RunPython(
            enable_rls_for_all_models,
            disable_rls_for_all_models
        ),
    ]