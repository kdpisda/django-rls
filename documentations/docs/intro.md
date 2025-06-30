---
sidebar_position: 1
---

# Introduction

Django RLS provides PostgreSQL Row Level Security (RLS) capabilities for Django applications, implementing true database-level security rather than application-layer filtering.

## What is Row Level Security?

Row Level Security (RLS) is a PostgreSQL feature that enables fine-grained access control at the row level. When RLS is enabled on a table, PostgreSQL automatically filters rows based on policies you define, ensuring users can only see and modify data they're authorized to access.

## Why Django RLS?

- **Database-Level Security**: Security is enforced by PostgreSQL, not your application code
- **Performance**: Filtering happens at the database level, often more efficiently
- **Consistency**: No risk of forgetting to filter querysets in your views
- **Simplicity**: Define policies once, apply everywhere
- **Django Integration**: Seamless integration with Django's ORM and middleware

## Key Features

- 🔒 True database-level Row Level Security
- 🏢 Built-in tenant-based and user-based policies
- 🔧 Extensible policy system for custom rules
- ⚡ Automatic context management via middleware
- 🧪 Comprehensive test utilities
- 📖 Django-style API following DRF patterns

## How It Works

1. **Define Models**: Inherit from `RLSModel` instead of Django's `Model`
2. **Add Policies**: Define RLS policies in your model's Meta class
3. **Middleware**: Automatically sets user/tenant context from requests
4. **Transparent**: Your views and querysets work normally - filtering is automatic

## Example

```python
from django_rls.models import RLSModel
from django_rls.policies import UserPolicy

class Document(RLSModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner'),
        ]
```

With this setup, users automatically see only their own documents - no additional filtering needed in your views!