---
sidebar_position: 1
---

# Policies

Django RLS provides several built-in policy types and allows you to create custom policies for any use case.

## Built-in Policies

### UserPolicy

Filters rows based on a user foreign key field:

```python
from django_rls.policies import UserPolicy

class Document(RLSModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner'),
        ]
```

**Options:**
- `user_field`: The field name containing the user foreign key (default: 'user')
- `operation`: SQL operation (ALL, SELECT, INSERT, UPDATE, DELETE)
- `permissive`: Whether the policy is permissive (True) or restrictive (False)

### TenantPolicy

Perfect for multi-tenant applications:

```python
from django_rls.policies import TenantPolicy

class TenantData(RLSModel):
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    
    class Meta:
        rls_policies = [
            TenantPolicy('tenant_policy', tenant_field='tenant'),
        ]
```

**Options:**
- `tenant_field`: The field name containing the tenant foreign key
- `operation`: SQL operation (ALL, SELECT, INSERT, UPDATE, DELETE)
- `permissive`: Whether the policy is permissive (True) or restrictive (False)

### CustomPolicy

For complex business logic:

```python
from django_rls.policies import CustomPolicy

class ComplexModel(RLSModel):
    status = models.CharField(max_length=20)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=50)
    
    class Meta:
        rls_policies = [
            CustomPolicy(
                'complex_policy',
                expression="""
                    status = 'published' 
                    OR owner_id = current_setting('rls.user_id')::integer
                    OR department = current_setting('rls.department', true)
                """
            ),
        ]
```

## Policy Operations

Policies can be applied to specific SQL operations:

```python
class SecureModel(RLSModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        rls_policies = [
            # Users can only see their own records
            UserPolicy('select_policy', operation='SELECT'),
            # Users can only update their own records
            UserPolicy('update_policy', operation='UPDATE'),
            # Anyone can insert
            CustomPolicy('insert_policy', operation='INSERT', 
                        expression='true'),
        ]
```

## Permissive vs Restrictive Policies

### Permissive (default)
At least one permissive policy must pass:

```python
rls_policies = [
    # User can access if they own it OR if it's public
    UserPolicy('owner_policy', permissive=True),
    CustomPolicy('public_policy', expression='is_public = true', 
                permissive=True),
]
```

### Restrictive
ALL restrictive policies must pass:

```python
rls_policies = [
    # User must own it AND it must be active
    UserPolicy('owner_policy', permissive=False),
    CustomPolicy('active_policy', expression='is_active = true', 
                permissive=False),
]
```

## Combining Policies

You can combine multiple policies for complex access control:

```python
class Project(RLSModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ManyToManyField(User, related_name='team_projects')
    is_public = models.BooleanField(default=False)
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    
    class Meta:
        rls_policies = [
            # Tenant isolation (restrictive - must always apply)
            TenantPolicy('tenant_isolation', permissive=False),
            # Access if owner
            UserPolicy('owner_access', user_field='owner'),
            # Access if team member
            CustomPolicy(
                'team_access',
                expression="""
                    id IN (
                        SELECT project_id FROM myapp_project_team 
                        WHERE user_id = current_setting('rls.user_id')::integer
                    )
                """
            ),
            # Access if public
            CustomPolicy('public_access', expression='is_public = true'),
        ]
```

## Dynamic Context Variables

You can use custom context variables in policies:

```python
# In your middleware or view
from django_rls.db.functions import set_rls_context

def set_user_department(request):
    if request.user.is_authenticated:
        set_rls_context('department', request.user.profile.department)

# In your policy
CustomPolicy(
    'department_policy',
    expression="department = current_setting('rls.department', true)"
)
```

## Policy Best Practices

1. **Start Simple**: Begin with basic UserPolicy or TenantPolicy
2. **Test Thoroughly**: Use Django RLS test utilities to verify policies
3. **Consider Performance**: Complex expressions can impact query performance
4. **Use Indexes**: Create indexes on fields used in policies
5. **Document Policies**: Clearly document the business logic behind each policy

## Security Considerations

- Field names are validated to prevent SQL injection
- Always use parameterized queries for dynamic values
- Test policies with different user roles
- Consider using restrictive policies for sensitive data
- Regularly audit policy effectiveness

## Creating Custom Policy Classes

For reusable policy logic:

```python
from django_rls.policies import BasePolicy

class DepartmentPolicy(BasePolicy):
    """Policy for department-based access control."""
    
    def __init__(self, name: str, department_field: str = 'department', **kwargs):
        self.department_field = department_field
        super().__init__(name, **kwargs)
    
    def get_sql_expression(self) -> str:
        return f"{self.department_field} = current_setting('rls.department', true)"

# Usage
class DepartmentData(RLSModel):
    department = models.CharField(max_length=50)
    
    class Meta:
        rls_policies = [
            DepartmentPolicy('dept_policy'),
        ]
```