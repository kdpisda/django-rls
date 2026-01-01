# Django RLS

[![PyPI version](https://badge.fury.io/py/django-rls.svg)](https://badge.fury.io/py/django-rls)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/django-rls)](https://pypi.org/project/django-rls/)
[![CI](https://github.com/kdpisda/django-rls/actions/workflows/ci.yml/badge.svg)](https://github.com/kdpisda/django-rls/actions/workflows/ci.yml)
[![Documentation](https://github.com/kdpisda/django-rls/actions/workflows/deploy-docs.yml/badge.svg)](https://django-rls.com)
[![codecov](https://codecov.io/gh/kdpisda/django-rls/branch/main/graph/badge.svg)](https://codecov.io/gh/kdpisda/django-rls)
[![Python Version](https://img.shields.io/pypi/pyversions/django-rls)](https://pypi.org/project/django-rls/)
[![Django Version](https://img.shields.io/badge/django-5.0%20%7C%205.1%20%7C%205.2%20%7C%206.0-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/pypi/l/django-rls)](LICENSE)

A Django package that provides PostgreSQL Row Level Security (RLS) capabilities at the database level.

See [CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security

See [SECURITY.md](.github/SECURITY.md).

## Features

- 🔒 Database-level Row Level Security using PostgreSQL RLS
- 🏢 Tenant-based and user-based policies
- 🐍 **Pythonic Policies**: Define policies using standard Django `Q` objects
- 🌳 **Hierarchical RLS**: Support for recursive CTEs and nested organizations
- ⚡ **Context Processors**: Inject dynamic context variables (e.g. user IP, session data)
- 🔧 Django 5.0, 5.1, 5.2 (LTS), and 6.0 support
- 🧪 Comprehensive test coverage
- 📖 Extensible policy system
- ⚡ Performance optimized

## Quick Start

```python
from django.db import models
from django.db.models import Q
from django_rls.models import RLSModel
from django_rls.policies import ModelPolicy, RLS

class Project(RLSModel):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)

    class Meta:
        rls_policies = [
            # Pythonic Policy: Owner OR Public
            ModelPolicy(
                'access_policy',
                filters=Q(owner=RLS.user_id()) | Q(is_public=True)
            ),
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
- Django 5.0, 5.1, 5.2 (LTS), or 6.0
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
