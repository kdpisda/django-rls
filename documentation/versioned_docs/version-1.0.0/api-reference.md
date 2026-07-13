---
sidebar_position: 10
---

# API Reference

Complete API documentation for Django RLS.

## Models

### RLSModel

Base class for models that use Row Level Security.

```python
from django_rls.models import RLSModel

class MyModel(RLSModel):
    # Your fields here

    class Meta:
        rls_policies = [
            # List of policies
        ]
```

**Class Methods:**

- `enable_rls()` - Enable RLS for this model
- `disable_rls()` - Disable RLS for this model
- `get_rls_policies()` - Get list of policies defined for this model

**Meta Options:**

- `rls_policies` - List of policy instances to apply to this model

## Policies

### BasePolicy

Abstract base class for all policies.

```python
from django_rls.policies import BasePolicy

class CustomPolicy(BasePolicy):
    def get_sql_expression(self) -> str:
        return "your SQL expression"
```

**Parameters:**
- `name` (str) - Unique name for the policy
- `operation` (str) - SQL operation: 'ALL', 'SELECT', 'INSERT', 'UPDATE', 'DELETE'
- `permissive` (bool) - Whether policy is permissive (True) or restrictive (False)
- `roles` (str) - PostgreSQL roles to apply to (default: 'public')

### UserPolicy

Policy for user-based access control.

```python
from django_rls.policies import UserPolicy

UserPolicy(
    name='owner_policy',
    user_field='owner',  # Foreign key field name
    operation='ALL',
    permissive=True
)
```

**Parameters:**
- `name` (str) - Policy name
- `user_field` (str) - Name of the foreign key field to User model
- `operation` (str) - SQL operation (default: 'ALL')
- `permissive` (bool) - Policy type (default: True)

### TenantPolicy

Policy for tenant-based isolation.

```python
from django_rls.policies import TenantPolicy

TenantPolicy(
    name='tenant_isolation',
    tenant_field='tenant',  # Foreign key field name
    operation='ALL',
    permissive=False  # Often restrictive for tenant isolation
)
```

**Parameters:**
- `name` (str) - Policy name
- `tenant_field` (str) - Name of the foreign key field to tenant model
- `operation` (str) - SQL operation (default: 'ALL')
- `permissive` (bool) - Policy type (default: True)

- `permissive` (bool) - Policy type (default: True)

### ModelPolicy

**Recommended** policy type using Django `Q` objects.

```python
from django_rls.policies import ModelPolicy
from django_rls.policies import RLS
from django.db.models import Q

ModelPolicy(
    name='pythonic_policy',
    filters=Q(owner=RLS.user_id()) | Q(is_public=True)
)
```

**Parameters:**
- `name` (str) - Policy name
- `filters` (Q) - Django Q object defining the access conditions
- `annotations` (dict) - Optional annotations for complex logic (e.g. `RLS.context`)
- `operation` (str) - SQL operation (default: 'ALL')
- `permissive` (bool) - Policy type (default: True)

### RLS Helper

Helper class for accessing RLS context variables in `Q` objects.

**Methods:**
- `RLS.user_id()` - Returns expression for current user ID (supports Integer and UUID)
- `RLS.tenant_id()` - Returns expression for current tenant ID
- `RLS.context(name, output_field=None)` - Returns expression for arbitrary context variable

### CustomPolicy

Policy with custom SQL expression.

```python
from django_rls.policies import CustomPolicy

CustomPolicy(
    name='complex_policy',
    expression="status = 'active' AND (is_public OR owner_id = current_setting('rls.user_id')::int)"
)
```

**Parameters:**
- `name` (str) - Policy name
- `expression` (str) - SQL boolean expression
- `operation` (str) - SQL operation (default: 'ALL')
- `permissive` (bool) - Policy type (default: True)

## Middleware

### RLSContextMiddleware

Middleware that sets PostgreSQL session variables from request.

```python
MIDDLEWARE = [
    # ... other middleware
    'django_rls.middleware.RLSContextMiddleware',
]
```

**Behavior:**
- Extracts user ID from `request.user`
- Extracts tenant ID from `request.tenant`, `request.user.profile.tenant_id`, or `request.session['tenant_id']`
- Sets PostgreSQL session variables using `SET LOCAL`
- Clears context after request

**Customization:**

```python
from django_rls.middleware import RLSContextMiddleware

class CustomRLSMiddleware(RLSContextMiddleware):
    def _get_tenant_id(self, request):
        # Custom tenant extraction logic
        return tenant_id

    def _set_rls_context(self, request):
        super()._set_rls_context(request)
        # Set additional context
```

## Database Functions

### set_rls_context

Set a PostgreSQL session variable for RLS.

```python
from django_rls.db.functions import set_rls_context

set_rls_context('user_id', 123)
set_rls_context('tenant_id', 456)
set_rls_context('custom_var', 'value', is_local=True)
```

**Parameters:**
- `name` (str) - Variable name (without 'rls.' prefix)
- `value` (Any) - Variable value
- `is_local` (bool) - Use SET LOCAL (transaction-scoped) vs SET (session-scoped)

### get_rls_context

Get a PostgreSQL session variable value.

```python
from django_rls.db.functions import get_rls_context

user_id = get_rls_context('user_id')
tenant_id = get_rls_context('tenant_id', default=None)
```

**Parameters:**
- `name` (str) - Variable name (without 'rls.' prefix)
- `default` (Any) - Default value if variable not set

### RLSContext

Context manager for temporarily setting RLS context.

```python
from django_rls.db.functions import RLSContext

with RLSContext(user_id=123, tenant_id=456):
    # Code executed with this context
    documents = Document.objects.all()
# Context automatically cleared
```

## Schema Editor

### RLSDatabaseSchemaEditor

Extended schema editor with RLS operations.

```python
from django_rls.backends.postgresql import RLSDatabaseSchemaEditor

with connection.schema_editor() as schema_editor:
    schema_editor.enable_rls(Model)
    schema_editor.create_policy(Model, policy)
```

**Methods:**

- `enable_rls(model)` - Enable RLS on model's table
- `disable_rls(model)` - Disable RLS on model's table
- `force_rls(model)` - Force RLS (even for table owner)
- `create_policy(model, policy)` - Create a policy
- `drop_policy(model, policy_name)` - Drop a policy
- `alter_policy(model, policy)` - Alter existing policy

## Migration Operations

### EnableRLS

Migration operation to enable RLS.

```python
from django_rls.migration_operations import EnableRLS

operations = [
    EnableRLS('myapp', 'MyModel'),
]
```

### DisableRLS

Migration operation to disable RLS.

```python
from django_rls.migration_operations import DisableRLS

operations = [
    DisableRLS('myapp', 'MyModel'),
]
```

### CreatePolicy

Migration operation to create a policy.

```python
from django_rls.migration_operations import CreatePolicy
from django_rls.policies import UserPolicy

operations = [
    CreatePolicy(
        'myapp',
        'MyModel',
        UserPolicy('owner_policy', user_field='owner')
    ),
]
```

### DropPolicy

Migration operation to drop a policy.

```python
from django_rls.migration_operations import DropPolicy

operations = [
    DropPolicy('myapp', 'MyModel', 'policy_name'),
]
```

## Exceptions

### PolicyError

Raised when policy configuration is invalid.

```python
from django_rls.exceptions import PolicyError

try:
    policy = UserPolicy('invalid_policy', user_field='')
except PolicyError as e:
    print(f"Invalid policy: {e}")
```

### ConfigurationError

Raised when RLS configuration is invalid.

```python
from django_rls.exceptions import ConfigurationError

try:
    class BadModel(RLSModel):
        class Meta:
            rls_policies = "not_a_list"  # Should be a list
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Test Utilities

### RLSTestMixin

Mixin providing RLS testing utilities.

```python
from django_rls.test import RLSTestMixin
from django.test import TestCase

class MyTest(RLSTestMixin, TestCase):
    def test_something(self):
        with self.disable_rls(Model):
            # Test with RLS disabled

        with self.as_user(user):
            # Test with specific user context

        with self.with_context(user_id=1, tenant_id=2):
            # Test with custom context
```

**Methods:**

- `disable_rls(model)` - Context manager to temporarily disable RLS
- `as_user(user)` - Context manager to set user context
- `with_context(**kwargs)` - Context manager to set arbitrary context

## Settings

### DJANGO_RLS

Optional settings dict for Django RLS configuration.

```python
DJANGO_RLS = {
    'DEFAULT_SCHEMA_EDITOR': 'django_rls.backends.postgresql.RLSDatabaseSchemaEditor',
    'CONTEXT_PROCESSOR': 'myapp.rls.custom_context_processor', # Deprecated
    'AUTO_ENABLE_RLS': True,  # Enable RLS automatically in migrations
    'POLICY_NAMING_CONVENTION': '{model_name}_{policy_type}_policy',
}
```

### RLS_CONTEXT_PROCESSORS

List of dotted paths to callables that return a dictionary of context variables to set in Postgres.

```python
# settings.py
RLS_CONTEXT_PROCESSORS = [
    'myapp.context.user_email_processor',
    'myapp.context.subscription_status_processor',
]
```

Each processor receives the `request` object and should return a dict or None.

## Signals

### pre_enable_rls

Sent before enabling RLS on a model.

```python
from django_rls.signals import pre_enable_rls

@receiver(pre_enable_rls)
def before_enable_rls(sender, model, **kwargs):
    print(f"About to enable RLS for {model}")
```

### post_enable_rls

Sent after enabling RLS on a model.

```python
from django_rls.signals import post_enable_rls

@receiver(post_enable_rls)
def after_enable_rls(sender, model, **kwargs):
    print(f"RLS enabled for {model}")
```
