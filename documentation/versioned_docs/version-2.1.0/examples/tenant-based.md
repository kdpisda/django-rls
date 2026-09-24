---
sidebar_position: 2
---

# Multi-Tenant Applications

Build secure multi-tenant applications where data is completely isolated between tenants.

## The Multi-Tenant Challenge

In multi-tenant applications, ensuring complete data isolation is critical:

```python
# Without RLS - Dangerous if you forget to filter!
def product_list(request):
    # WRONG: Could expose other tenants' data
    products = Product.objects.all()

    # RIGHT: Must always remember tenant filtering
    products = Product.objects.filter(tenant=request.user.tenant)
```

## Complete Multi-Tenant Solution

### 1. Tenant Model

```python
from django.db import models

class Tenant(models.Model):
    name = models.CharField(max_length=100)
    subdomain = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
```

### 2. User-Tenant Relationship

```python
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='users'
    )
```

### 3. Tenant-Aware Models

We use `ModelPolicy` to ensure that every query is automatically filtered by the current tenant ID.

```python
from django.db.models import Q
from django_rls.models import RLSModel
from django_rls.policies import ModelPolicy, RLS

class Customer(RLSModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField()

    class Meta:
        rls_policies = [
            # Standard Tenant Isolation using Q objects
            ModelPolicy(
                'tenant_isolation',
                filters=Q(tenant=RLS.tenant_id())
            ),
        ]

class Product(RLSModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        rls_policies = [
            ModelPolicy(
                'tenant_isolation',
                filters=Q(tenant=RLS.tenant_id())
            ),
        ]
```

#### Note on Shortcuts
For simple cases where you just want to filter by a foreign key, you *can* use the built-in `TenantPolicy`:

```python
from django_rls.policies import TenantPolicy
# Equivalent to Q(tenant=RLS.tenant_id())
TenantPolicy('isolation', tenant_field='tenant')
```
However, `ModelPolicy` is recommended as it allows you to easily add complex logic later (e.g., OR `is_global=True`).

### 4. Tenant Detection Middleware

```python
from django_rls.middleware import RLSContextMiddleware

class TenantMiddleware:
    """Detect tenant from subdomain."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract subdomain
        host = request.get_host().split(':')[0]
        subdomain = host.split('.')[0]

        try:
            request.tenant = Tenant.objects.get(
                subdomain=subdomain,
                is_active=True
            )
        except Tenant.DoesNotExist:
            request.tenant = None

        return self.get_response(request)

# In settings.py
MIDDLEWARE = [
    # ... other middleware
    'myapp.middleware.TenantMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_rls.middleware.RLSContextMiddleware',
]
```

### 5. Views Are Simple

```python
@login_required
def customer_list(request):
    # Automatically filtered to current tenant!
    customers = Customer.objects.all()
    return render(request, 'customers/list.html', {
        'customers': customers,
        'tenant': request.tenant,
    })

@login_required
def dashboard(request):
    # All queries respect tenant isolation
    context = {
        'customer_count': Customer.objects.count(),
        'product_count': Product.objects.count(),
        'recent_orders': Order.objects.order_by('-created_at')[:10],
        'total_revenue': Order.objects.aggregate(Sum('total')),
    }
    return render(request, 'dashboard.html', context)
```

## Advanced Multi-Tenant Patterns

### Cross-Tenant Data Sharing

Some data might be shared across tenants (Global products + Tenant customizations).

```python
class GlobalProduct(RLSModel):
    """Products available to all tenants."""
    name = models.CharField(max_length=200)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)

    # No RLS policies - accessible to all

class TenantProduct(RLSModel):
    """Tenant-specific product customization."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    global_product = models.ForeignKey(GlobalProduct, on_delete=models.CASCADE)
    custom_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        rls_policies = [
            ModelPolicy(
                'tenant_isolation',
                filters=Q(tenant=RLS.tenant_id())
            ),
        ]
        unique_together = [['tenant', 'global_product']]
```

### Tenant Admin Users

Allow specific users (e.g. Support Staff) to access multiple tenants via an explicit membership table.

```python
class TenantUser(RLSModel):
    """User access to specific tenants."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[
        ('admin', 'Admin'),
        ('member', 'Member'),
    ])

    class Meta:
        rls_policies = [
            # Users can see their own tenant memberships
            ModelPolicy('user_access', filters=Q(user=RLS.user_id()))
        ]

class MultiTenantModel(RLSModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    # ... other fields

    class Meta:
        rls_policies = [
            # "Access if my tenant_id is in the list of tenants I belong to"
            ModelPolicy(
                'multi_tenant_access',
                filters=Q(
                    tenant__in=Subquery(
                        TenantUser.objects.filter(
                            user=RLS.user_id()
                        ).values('tenant')
                    )
                )
            ),
        ]
```
*Note: `django-rls` usually handles subqueries automatically, but explicit `Subquery` usage is fully supported for complex joins.*

## Performance Optimization

### Indexes for Tenant Fields

```python
class TenantModel(RLSModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, db_index=True)
    # ... other fields

    class Meta:
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
        ]
```

### Best Practices

1. **Always include tenant field** in RLS-enabled models
2. **Use database constraints** to ensure referential integrity
3. **Index tenant fields** for performance
4. **Test tenant isolation** thoroughly
