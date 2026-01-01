---
sidebar_position: 3
---

# Management Commands

Django RLS provides management commands to help you manage Row Level Security in your database.

## enable_rls

Enable Row Level Security for all RLSModel subclasses or specific models.

### Usage

```bash
# Enable RLS for all models
python manage.py enable_rls

# Enable RLS for specific models
python manage.py enable_rls myapp.Document myapp.Task

# Enable RLS for all models in an app
python manage.py enable_rls myapp

# Force enable (recreate policies)
python manage.py enable_rls --force
```

### Options

- `models`: Optional list of app labels or model names
- `--force`: Drop and recreate existing policies
- `--dry-run`: Show what would be done without making changes

### What It Does

1. Enables RLS on the table: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
2. Creates all policies defined in the model's Meta.rls_policies
3. Sets up policy permissions

### Example Output

```
Enabling RLS for myapp.Document...
  ✓ Enabled RLS on table myapp_document
  ✓ Created policy: owner_policy
  ✓ Created policy: tenant_policy
  
Enabling RLS for myapp.Task...
  ✓ Enabled RLS on table myapp_task
  ✓ Created policy: user_policy
  
Successfully enabled RLS for 2 models.
```

## disable_rls

Disable Row Level Security for models.

### Usage

```bash
# Disable RLS for all models
python manage.py disable_rls

# Disable RLS for specific models
python manage.py disable_rls myapp.Document

# Disable and keep policies
python manage.py disable_rls --keep-policies
```

### Options

- `models`: Optional list of app labels or model names
- `--keep-policies`: Don't drop policies, just disable RLS
- `--dry-run`: Show what would be done without making changes

### Example Output

```
Disabling RLS for myapp.Document...
  ✓ Dropped policy: owner_policy
  ✓ Dropped policy: tenant_policy
  ✓ Disabled RLS on table myapp_document
  
Successfully disabled RLS for 1 model.
```

## rls_status

Check the current RLS status of your models.

### Usage

```bash
# Check all models
python manage.py rls_status

# Check specific models
python manage.py rls_status myapp.Document

# Verbose output
python manage.py rls_status --verbose
```

### Example Output

```
RLS Status Report
================

myapp.Document:
  ✓ RLS Enabled
  Policies:
    - owner_policy (PERMISSIVE, FOR ALL)
    - tenant_policy (RESTRICTIVE, FOR ALL)
    
myapp.Task:
  ✗ RLS Disabled
  Defined policies (not active):
    - user_policy
    
myapp.Comment:
  ⚠ No RLS policies defined
  
Summary:
- Models with RLS enabled: 1
- Models with RLS disabled: 1
- Models without RLS policies: 1
```

## rls_sync

Synchronize database RLS state with model definitions.

### Usage

```bash
# Sync all models
python manage.py rls_sync

# Sync specific app
python manage.py rls_sync myapp

# Show differences without applying
python manage.py rls_sync --dry-run
```

### What It Does

1. Compares model policies with database policies
2. Adds missing policies
3. Updates changed policies
4. Removes undefined policies
5. Ensures RLS is enabled where needed

### Example Output

```
Synchronizing RLS policies...

myapp.Document:
  + Adding policy: visibility_policy (new in model)
  ~ Updating policy: owner_policy (expression changed)
  - Removing policy: old_policy (not in model)
  
myapp.Task:
  ✓ No changes needed
  
Applied 3 changes.
```

## Creating Custom Commands

You can create custom management commands that work with RLS:

```python
# myapp/management/commands/check_rls_coverage.py
from django.core.management.base import BaseCommand
from django.apps import apps
from django_rls.models import RLSModel

class Command(BaseCommand):
    help = 'Check which models should have RLS but don\'t'
    
    def handle(self, *args, **options):
        for model in apps.get_models():
            # Skip if already using RLS
            if issubclass(model, RLSModel):
                continue
                
            # Check if model has user or tenant fields
            fields = model._meta.get_fields()
            has_user = any(f.name in ['user', 'owner', 'created_by'] 
                          for f in fields)
            has_tenant = any(f.name in ['tenant', 'organization'] 
                           for f in fields)
            
            if has_user or has_tenant:
                self.stdout.write(
                    self.style.WARNING(
                        f'{model._meta.label} could benefit from RLS'
                    )
                )
```

## Command Best Practices

1. **Always backup** before running commands in production
2. **Use --dry-run** to preview changes
3. **Test in development** first
4. **Monitor performance** after enabling RLS
5. **Document policy changes** in your changelog

## Automation

You can automate RLS setup in your deployment:

```python
# In your post-deployment script
from django.core.management import call_command

# Enable RLS after migrations
call_command('migrate')
call_command('enable_rls')

# Or in a migration
from django.db import migrations

def enable_rls_policies(apps, schema_editor):
    from django.core.management import call_command
    call_command('enable_rls', 'myapp')

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(enable_rls_policies),
    ]
```