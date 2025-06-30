# Django RLS

[![CI](https://github.com/kdpisda/django-rls/actions/workflows/ci.yml/badge.svg)](https://github.com/kdpisda/django-rls/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/kdpisda/django-rls/branch/main/graph/badge.svg)](https://codecov.io/gh/kdpisda/django-rls)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://pypi.org/project/django-rls/)
[![Django Version](https://img.shields.io/badge/django-5.0%20%7C%205.1%20%7C%205.2-blue.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-BSD%203--Clause-blue.svg)](LICENSE)

A Django package that provides PostgreSQL Row Level Security (RLS) capabilities at the database level.

## Features

- 🔒 Database-level Row Level Security using PostgreSQL RLS
- 🏢 Tenant-based and user-based policies
- 🔧 Django 5.0, 5.1, and 5.2 (LTS) support
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

### Requirements

- Python 3.10, 3.11, 3.12, or 3.13
- Django 5.0, 5.1, or 5.2 (LTS)
- PostgreSQL 12 or higher (tested with PostgreSQL 17)

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

Full documentation is available at [kdpisda.github.io/django-rls](https://kdpisda.github.io/django-rls/)

### Quick Links

- [Getting Started](https://kdpisda.github.io/django-rls/docs/intro)
- [Installation Guide](https://kdpisda.github.io/django-rls/docs/installation)
- [API Reference](https://kdpisda.github.io/django-rls/docs/api-reference)
- [Examples](https://kdpisda.github.io/django-rls/docs/examples/basic-usage)

## License

BSD 3-Clause License - see LICENSE file for details.