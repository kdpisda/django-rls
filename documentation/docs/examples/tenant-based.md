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

```python
from django_rls.models import RLSModel
from django_rls.policies import TenantPolicy

class Customer(RLSModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    
    class Meta:
        rls_policies = [
            TenantPolicy('tenant_isolation', tenant_field='tenant'),
        ]

class Product(RLSModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        rls_policies = [
            TenantPolicy('tenant_isolation', tenant_field='tenant'),
        ]

class Order(RLSModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        rls_policies = [
            TenantPolicy('tenant_isolation', tenant_field='tenant'),
        ]
```

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

### Tenant-Specific Settings

```python
class TenantSettings(RLSModel):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE)
    theme_color = models.CharField(max_length=7, default='#007bff')
    logo = models.ImageField(upload_to='tenant_logos/', null=True)
    features = models.JSONField(default=dict)
    
    class Meta:
        rls_policies = [
            TenantPolicy('tenant_isolation', tenant_field='tenant'),
        ]
```

### Cross-Tenant Data Sharing

Some data might be shared across tenants:

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
            TenantPolicy('tenant_isolation', tenant_field='tenant'),
        ]
        unique_together = [['tenant', 'global_product']]
```

### Tenant Admin Users

Allow admin users to access multiple tenants:

```python
class TenantUser(RLSModel):
    """User access to specific tenants."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    ])
    
    class Meta:
        rls_policies = [
            # Users can see their own tenant memberships
            UserPolicy('user_access', user_field='user'),
        ]

class MultiTenantModel(RLSModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    # ... other fields
    
    class Meta:
        rls_policies = [
            CustomPolicy(
                'multi_tenant_access',
                expression="""
                    tenant_id IN (
                        SELECT tenant_id FROM myapp_tenantuser
                        WHERE user_id = current_setting('rls.user_id')::integer
                    )
                """
            ),
        ]
```

## Testing Multi-Tenant Applications

```python
from django.test import TestCase
from django_rls.test import RLSTestMixin

class TenantIsolationTest(RLSTestMixin, TestCase):
    def setUp(self):
        # Create tenants
        self.tenant1 = Tenant.objects.create(
            name='Acme Corp',
            subdomain='acme'
        )
        self.tenant2 = Tenant.objects.create(
            name='Globex Inc',
            subdomain='globex'
        )
        
        # Create users
        self.user1 = User.objects.create_user(
            username='john',
            tenant=self.tenant1
        )
        self.user2 = User.objects.create_user(
            username='jane',
            tenant=self.tenant2
        )
    
    def test_tenant_isolation(self):
        # Create data for tenant1
        with self.with_context(user_id=self.user1.id, 
                              tenant_id=self.tenant1.id):
            Customer.objects.create(
                tenant=self.tenant1,
                name='Acme Customer'
            )
        
        # Verify tenant2 cannot see it
        with self.with_context(user_id=self.user2.id,
                              tenant_id=self.tenant2.id):
            customers = Customer.objects.all()
            self.assertEqual(customers.count(), 0)
```

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

### Tenant-Specific Database Connections

For large-scale applications:

```python
class TenantDatabaseRouter:
    """Route queries to tenant-specific databases."""
    
    def db_for_read(self, model, **hints):
        if hasattr(model, '_meta') and hasattr(model._meta, 'rls_policies'):
            # Get current tenant from thread-local storage
            tenant_id = getattr(_thread_locals, 'tenant_id', None)
            if tenant_id:
                return f'tenant_{tenant_id}'
        return 'default'
```

## Best Practices

1. **Always include tenant field** in RLS-enabled models
2. **Use database constraints** to ensure referential integrity
3. **Index tenant fields** for performance
4. **Test tenant isolation** thoroughly
5. **Monitor query performance** per tenant
6. **Plan for tenant data migration** and archival