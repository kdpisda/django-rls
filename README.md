# Django RLS

[![PyPI version](https://badge.fury.io/py/django-rls.svg)](https://badge.fury.io/py/django-rls)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/django-rls)](https://pypi.org/project/django-rls/)
[![CI](https://github.com/kdpisda/django-rls/actions/workflows/ci.yml/badge.svg)](https://github.com/kdpisda/django-rls/actions/workflows/ci.yml)
[![Documentation](https://github.com/kdpisda/django-rls/actions/workflows/deploy-docs.yml/badge.svg)](https://django-rls.com)
[![codecov](https://codecov.io/gh/kdpisda/django-rls/branch/main/graph/badge.svg)](https://codecov.io/gh/kdpisda/django-rls)
[![Python Version](https://img.shields.io/pypi/pyversions/django-rls)](https://pypi.org/project/django-rls/)
[![Django Version](https://img.shields.io/badge/django-5.0%20%7C%205.1%20%7C%205.2-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/pypi/l/django-rls)](LICENSE)

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

Install from PyPI:

```bash
pip install django-rls
```

Or install the latest development version:

```bash
pip install git+https://github.com/kdpisda/django-rls.git
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

Full documentation is available at [django-rls.com](https://django-rls.com)

### Quick Links

- [Getting Started](https://django-rls.com/docs/intro)
- [Installation Guide](https://django-rls.com/docs/installation)
- [API Reference](https://django-rls.com/docs/api-reference)
- [Examples](https://django-rls.com/docs/examples/basic-usage)

## License

BSD 3-Clause License - see LICENSE file for details.