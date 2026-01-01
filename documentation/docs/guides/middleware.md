---
sidebar_position: 2
---

# Middleware

The RLSContextMiddleware is responsible for setting PostgreSQL session variables that your RLS policies use for filtering.

## How It Works

1. Extracts user and tenant information from the request
2. Sets PostgreSQL session variables using `SET LOCAL`
3. These variables are available to RLS policies during the request
4. Clears the context after the request completes

## Basic Setup

Add the middleware after Django's authentication middleware:

```python
MIDDLEWARE = [
    # ... other middleware
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_rls.middleware.RLSContextMiddleware',  # Must be after auth
    # ... other middleware
]
```

## Default Behavior

By default, the middleware sets:

- `rls.user_id`: The ID of the authenticated user
- `rls.tenant_id`: Extracted from the request (if available)

## Customizing Context Extraction

### Custom Tenant Detection

The middleware looks for tenant information in this order:

1. `request.tenant` (set by other middleware)
2. `request.user.profile.tenant_id`
3. `request.session['tenant_id']`

You can customize this by subclassing:

```python
from django_rls.middleware import RLSContextMiddleware

class CustomRLSMiddleware(RLSContextMiddleware):
    def _get_tenant_id(self, request):
        # Custom logic to extract tenant
        if hasattr(request, 'organization'):
            return request.organization.id
        
        # From subdomain
        host = request.get_host()
        subdomain = host.split('.')[0]
        try:
            from myapp.models import Tenant
            tenant = Tenant.objects.get(subdomain=subdomain)
            return tenant.id
        except Tenant.DoesNotExist:
            return None
```

### Adding Custom Context Variables

```python
from django_rls.middleware import RLSContextMiddleware
from django_rls.db.functions import set_rls_context

class ExtendedRLSMiddleware(RLSContextMiddleware):
    def _set_rls_context(self, request):
        # Call parent to set user_id and tenant_id
        super()._set_rls_context(request)
        
        # Add custom context
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            set_rls_context('department', profile.department)
            set_rls_context('role', profile.role)
            set_rls_context('region', profile.region)
```

## Context Variables in Policies

Use the context variables in your policies:

```python
class RegionalData(RLSModel):
    region = models.CharField(max_length=50)
    
    class Meta:
        rls_policies = [
            CustomPolicy(
                'region_policy',
                expression="region = current_setting('rls.region', true)"
            ),
        ]
```

## Handling Anonymous Users

The middleware handles anonymous users gracefully:

```python
class PublicRLSMiddleware(RLSContextMiddleware):
    def _set_rls_context(self, request):
        if request.user.is_authenticated:
            super()._set_rls_context(request)
        else:
            # Set a special context for anonymous users
            set_rls_context('user_id', '-1')
            set_rls_context('is_anonymous', 'true')
```

## Performance Considerations

1. **Minimize Context Calls**: Set all context variables at once
2. **Cache Lookups**: Cache tenant lookups if they're expensive
3. **Use Connection Pooling**: RLS context is per-connection

Example with caching:

```python
from django.core.cache import cache

class CachedTenantMiddleware(RLSContextMiddleware):
    def _get_tenant_id(self, request):
        if not request.user.is_authenticated:
            return None
            
        cache_key = f'user_tenant_{request.user.id}'
        tenant_id = cache.get(cache_key)
        
        if tenant_id is None:
            tenant_id = request.user.profile.tenant_id
            cache.set(cache_key, tenant_id, 300)  # Cache for 5 minutes
            
        return tenant_id
```

## Testing with Middleware

When testing, you can set context manually:

```python
from django.test import TestCase
from django_rls.db.functions import set_rls_context

class MyTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser')
        self.tenant = Tenant.objects.create(name='Test Tenant')
        
    def test_with_context(self):
        # Manually set context for tests
        set_rls_context('user_id', self.user.id)
        set_rls_context('tenant_id', self.tenant.id)
        
        # Your test code here
        documents = Document.objects.all()
        # ...
```

## Debugging Middleware

Enable debug logging to see what context is being set:

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django_rls': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Common Patterns

### Multi-Database Setup

```python
class MultiDBRLSMiddleware(RLSContextMiddleware):
    def _set_rls_context(self, request):
        # Set context for each database
        for db_alias in ['default', 'tenant_db']:
            with connections[db_alias].cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('rls.user_id', %s, true)",
                    [str(request.user.id)]
                )
```

### API Authentication

```python
class APIRLSMiddleware(RLSContextMiddleware):
    def _set_rls_context(self, request):
        # Handle both session and token auth
        if hasattr(request, 'auth'):
            # DRF token authentication
            set_rls_context('user_id', request.user.id)
            set_rls_context('api_key', request.auth.key)
        else:
            # Regular session auth
            super()._set_rls_context(request)
```