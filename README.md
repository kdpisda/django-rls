# Django RLS

A Django package that provides PostgreSQL Row Level Security (RLS) capabilities at the database level.

## Features

- 🔒 Database-level Row Level Security using PostgreSQL RLS
- 🏢 Tenant-based and user-based policies
- 🔧 Django 5.x compatibility
- 🧪 Comprehensive test coverage
- 📖 Extensible policy system
- ⚡ Performance optimized

## Quick Start

```python
from django_rls.models import RLSModel
from django_rls.policies import TenantPolicy, UserPolicy

class TenantAwareModel(RLSModel):
    name = models.CharField(max_length=100)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    
    class Meta:
        rls_policies = [
            TenantPolicy('tenant_policy', tenant_field='tenant'),
        ]
```

## Installation

```bash
pip install django-rls
```

Add to your Django settings:

```python
INSTALLED_APPS = [
    # ... your apps
    'django_rls',
]

MIDDLEWARE = [
    # ... your middleware
    'django_rls.middleware.RLSContextMiddleware',
]
```

## Documentation

Full documentation is available at [django-rls.readthedocs.io](https://django-rls.readthedocs.io)

## License

BSD 3-Clause License - see LICENSE file for details.