# Basic Usage Example

This example demonstrates basic user-based Row Level Security with Django RLS.

## Setup

1. Add the model to your Django app:

```python
from django.db import models
from django.contrib.auth.models import User

from django_rls.models import RLSModel
from django_rls.policies import UserPolicy


class UserDocument(RLSModel):
    """Document that belongs to a user."""
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        rls_policies = [
            UserPolicy('user_document_policy', user_field='user'),
        ]
```

2. Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

3. Enable RLS:

```bash
python manage.py enable_rls
```

## How it works

- Each user can only see their own documents
- The RLS policy is enforced at the database level
- The middleware automatically sets the user context from the request
- No additional filtering is needed in your views or querysets

## Usage in views

```python
from django.shortcuts import render
from .models import UserDocument

def document_list(request):
    # User will only see their own documents
    documents = UserDocument.objects.all()
    return render(request, 'documents/list.html', {'documents': documents})
```