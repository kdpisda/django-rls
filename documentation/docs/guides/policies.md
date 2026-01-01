---
sidebar_position: 1
---

# Defining Policies

Django RLS allows you to define Row Level Security policies using standard Django syntax (`Q` objects) or specialized helpers.

## Pythonic Policies (Recommended)

The most robust way to define policies is using `ModelPolicy` with `Q` objects. This ensures your policies evolve with your models and prevents SQL injection risks.

### Basic Example

```python
from django.db import models
from django.db.models import Q
from django_rls.models import RLSModel
from django_rls.policies import ModelPolicy, RLS

class Document(RLSModel):
    title = models.CharField(max_length=100)
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)

    class Meta:
        rls_policies = [
            # Allow access if User is Owner OR Document is Public
            ModelPolicy(
                'access_policy',
                filters=Q(owner=RLS.user_id()) | Q(is_public=True)
            )
        ]
```

### The `RLS` Helper

Use the `RLS` helper class to reference session variables inside your policies.

#### User & Tenant
*   `RLS.user_id()`: The current user's ID.
    *   **Flexible Types**: Automatically handles **Integer** or **UUID** primary keys based on your `AUTH_USER_MODEL`.
    *   **Lazy Evaluation**: The ID is resolved at query compilation time, ensuring compatibility with migrations.
*   `RLS.tenant_id()`: The current tenant's ID.

#### Custom Context
*   `RLS.context('variable_name', output_field=None)`: Access custom variables set by Context Processors.
    *   **Usage**: `Q(email=RLS.context('user_email', CharField()))`
    *   **Note**: Always provide `output_field` for non-integer types (e.g., Strings, Booleans) so the ORM generates correct SQL casts.

### Joined Field Support (Auto-Subqueries)

PostgreSQL RLS policies do not support `JOIN`s directly. However, `django-rls` automatically detects related field lookups and converts them to optimized subqueries.

**You can write:**
```python
ModelPolicy(
    'org_policy',
    filters=Q(organization__country='US')
)
```

**It automatically converts to SQL:**
```sql
organization_id IN (SELECT id FROM app_organization WHERE country = 'US')
```
*No more manual subquery writing!*

## Built-in Shortcuts

For common simple patterns, you can use these shortcuts:

### UserPolicy

Filters rows based on a user foreign key field.

```python
from django_rls.policies import UserPolicy

# Equivalent to: Q(owner=RLS.user_id())
UserPolicy('owner_policy', user_field='owner')
```

### TenantPolicy

Filters rows based on a tenant foreign key.

```python
from django_rls.policies import TenantPolicy

# Equivalent to: Q(tenant=RLS.tenant_id())
TenantPolicy('tenant_policy', tenant_field='tenant')
```

## Advanced: Custom SQL Policies

For strictly database-specific logic that cannot be expressed in Django ORM, you can use `CustomPolicy` with raw SQL.

```python
from django_rls.policies import CustomPolicy

CustomPolicy(
    'complex_sql_policy',
    expression="""
        status = 'active'
        AND (
            owner_id = current_setting('rls.user_id')::int
            OR EXISTS (SELECT 1 FROM team_members WHERE ...)
        )
    """
)
```

## Permissive vs Restrictive

*   **Permissive (Default)**: Policies are combined with `OR`. If *any* permissive policy passes, the row is visible.
*   **Restrictive**: Policies are combined with `AND`. *All* restrictive policies must pass.

```python
rls_policies = [
    # Must belong to Tenant (Restrictive)
    TenantPolicy('tenant_isolation', permissive=False),

    # Must be (Owner OR Public) (Permissive)
    ModelPolicy('access', filters=Q(owner=RLS.user_id()) | Q(is_public=True))
]
```
