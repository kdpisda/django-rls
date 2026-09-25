---
sidebar_position: 2
---

# Installation

## Requirements

- Python 3.10, 3.11, 3.12, or 3.13
- Django 5.0, 5.1, or 5.2 (LTS)
- PostgreSQL 12+ (tested with PostgreSQL 17)
- psycopg2-binary 2.9+

## Install via pip

```bash
pip install django-rls
```

## Install via Poetry

```bash
poetry add django-rls
```

## Django Configuration

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ... your other apps
    'django_rls',
]
```

### 2. Add Middleware

```python
MIDDLEWARE = [
    # ... other middleware
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Add RLS middleware after authentication
    'django_rls.middleware.RLSContextMiddleware',
]
```

### 3. Database Configuration

Ensure you're using PostgreSQL:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_database',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Database Permissions

Your database user needs permissions to:
- Create and drop policies
- Enable/disable RLS on tables

Grant these permissions:

```sql
-- Connect as superuser
GRANT ALL ON DATABASE your_database TO your_user;
```

## Verify Installation

```bash
python manage.py shell
```

```python
import django_rls
print(django_rls.__version__)
```

## Next Steps

- Follow the [Quick Start](quick-start.md) guide
- Learn about [Policies](guides/policies.md)
- See [Examples](examples/basic-usage.md)