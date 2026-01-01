---
sidebar_position: 2
---

# 1. Project Setup & Data Modeling

Let's start by defining our data model. We need to represent the organizational structure of MegaCorp and the resources we want to protect.

## Installation

First, ensure you have `django-rls` installed:

```bash
pip install django-rls
```

And add it to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'django_rls',
    'myapp',
]

MIDDLEWARE = [
    # ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Add RLS middleware AFTER authentication
    'django_rls.middleware.RLSContextMiddleware',
]
```

## The Data Model

Copy the following into your `myapp/models.py`.

We need three main components:
1.  **Department**: A hierarchical tree structure.
2.  **ERPDocument**: The sensitive resource we want to protect.
3.  **UserPermission**: A table to store specific collaborative exceptions.

```python
from django.db import models
from django.contrib.auth.models import User
from django_rls.models import RLSModel

# 1. Department Hierarchy
# Note: This is a standard Django model. We don't necessarily need RLS
# on the structure itself, everyone can likely see the org chart.
class Department(models.Model):
    name = models.CharField(max_length=100)
    # Self-referencing FK for hierarchy (e.g. Engineering -> Backend)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='sub_departments',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.name

# 2. Granular ACL Table
# Used to grant specific exceptions.
class UserPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    document_id = models.IntegerField() # Linking to ERPDocument ID loosely or via FK
    can_view = models.BooleanField(default=False)

# 3. The Protected Resource
# Inherits from RLSModel to enable Row Level Security
class ERPDocument(RLSModel):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    content = models.TextField()
    is_confidential = models.BooleanField(default=True)

    class Meta:
        rls_policies = [] # We will populate this next!
```

## Configuring the User

For our hierarchy rules to work, we need to know which Department a User belongs to. In a real app, you might have a `UserProfile` model.

```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
```

## Initial Migration

Run the migrations to create these tables in PostgreSQL.

```bash
python manage.py makemigrations
python manage.py migrate
```

At this stage, **RLS is not yet active**. We have defined the structure, but we haven't defined any policies yet. In the next chapter, we will implement the first layer of security.
