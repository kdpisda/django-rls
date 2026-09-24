---
sidebar_position: 3
---

# Quick Start

Get up and running with Django RLS in 5 minutes.

## 1. Install Django RLS

```bash
pip install django-rls
```

## 2. Configure Django Settings

Add to your `settings.py`:

```python
INSTALLED_APPS = [
    # ... your apps
    'django_rls',
]

MIDDLEWARE = [
    # ... other middleware
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_rls.middleware.RLSContextMiddleware',  # Add after auth
]
```

## 3. Create Your First RLS Model

```python
from django.db import models
from django.contrib.auth.models import User
from django_rls.models import RLSModel
from django_rls.policies import UserPolicy

class Task(RLSModel):
    title = models.CharField(max_length=200)
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner'),
        ]
```

## 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

`makemigrations` only tracks your Django model state — it does **not** write
`ENABLE ROW LEVEL SECURITY` or `CREATE POLICY` into the migration files. RLS
itself is applied separately, after `migrate` runs, via the `post_migrate`
signal (controlled by the [`AUTO_ENABLE_RLS`](guides/configuration.md#auto_enable_rls-default-true)
setting, which defaults to `True`).

If RLS doesn't seem to be active — for example `AUTO_ENABLE_RLS` is `False`,
you're not on the `django_rls.backends.postgresql` engine, or the
`post_migrate` signal failed silently — run it manually:

```bash
python manage.py enable_rls
```

Re-run `enable_rls` whenever you add a new `RLSModel` or change its
`rls_policies`. See [Management Commands](guides/management-commands.md#enable_rls)
for options, and [`rls_status`](guides/management-commands.md#rls_status) /
[`audit_rls`](guides/management-commands.md#audit_rls) for verifying RLS is
actually enabled (handy in CI).

## 5. Use Your Model

Your views work normally - RLS filtering is automatic:

```python
from django.shortcuts import render
from .models import Task

def task_list(request):
    # Users automatically see only their own tasks
    tasks = Task.objects.all()
    return render(request, 'tasks/list.html', {'tasks': tasks})
```

## That's It!

Users will only see their own tasks. No need to filter querysets manually:

- ✅ `Task.objects.all()` returns only the current user's tasks
- ✅ `Task.objects.create()` automatically sets the owner
- ✅ Updates and deletes are restricted to owned tasks
- ✅ Works with all QuerySet methods

## Next Steps

- Learn about [different policy types](guides/policies.md)
- Set up [multi-tenant filtering](examples/tenant-based.md)
- Understand [how policies work](guides/policies.md)
- Configure [testing](guides/testing.md)

## Common Patterns

### Multi-Tenant Application

```python
class TenantModel(RLSModel):
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    # ... other fields
    
    class Meta:
        rls_policies = [
            TenantPolicy('tenant_policy', tenant_field='tenant'),
        ]
```

### Public/Private Data

```python
class Document(RLSModel):
    is_public = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        rls_policies = [
            CustomPolicy(
                'visibility_policy',
                expression="is_public = true OR owner_id = current_setting('rls.user_id')::integer"
            ),
        ]
```

### Group-Based Access

```python
class GroupDocument(RLSModel):
    group = models.ForeignKey('auth.Group', on_delete=models.CASCADE)
    
    class Meta:
        rls_policies = [
            CustomPolicy(
                'group_policy',
                expression="""
                    group_id IN (
                        SELECT group_id FROM auth_user_groups 
                        WHERE user_id = current_setting('rls.user_id')::integer
                    )
                """
            ),
        ]
```