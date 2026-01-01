---
sidebar_position: 3
---

# 2. Basic Departmental Isolation

Our first requirement is **Strict Departmental Isolation**.

> A "Sales" employee must never see "Engineering" documents.

This seems simple, but it is the foundation of multi-tenant security.

## The Approach: Without django-rls

In a traditional Django application, you are responsible for enforcing this rule in every single place data is accessed.

### 1. The View Layer
You must remember to filter every QuerySet.

```python
# views.py (The Manual Way)
def document_list(request):
    # DANGER: If you type .all() here, you just leaked data!
    # docs = ERPDocument.objects.all()  <-- WRONG

    # You must always filter:
    user_dept = request.user.profile.department
    docs = ERPDocument.objects.filter(department=user_dept)

    return render(request, 'list.html', {'docs': docs})
```

### 2. The API Layer
If you use Django REST Framework, you must override `get_queryset` on every ViewSet.

```python
# api.py (The Manual Way)
class DocumentViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # Again, easy to forget or get wrong
        return ERPDocument.objects.filter(department=self.request.user.profile.department)
```

### 3. The Admin Panel
Often overlooked! By default, the Django Admin matches `queryset.all()`. This means any staff member can see **everything**. You have to override `get_queryset` in `admin.py` too.

### The Risk
If you have 50 views and you forget the filter in *just one*, you have a security breach.

---

## The Approach: With django-rls

With Row-Level Security, we move this logic **into the database**. We define it once, on the model, and it applies everywhere automatically.

### 1. Setting the Context

First, we need to ensure the database knows *which* department the current user belongs to. We use `django-rls` Context Middleware.

```python
# myapp/middleware.py
from django_rls.db.functions import set_rls_context

class MegaCorpMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            set_rls_context('user_id', request.user.id)

            # Set Department ID as 'tenant_id'
            try:
                dept_id = request.user.userprofile.department_id
                set_rls_context('tenant_id', dept_id)
            except AttributeError:
                pass

        return self.get_response(request)
```

### 2. Defining the Policy

Now we add the policy to `ERPDocument`.

```python
# myapp/models.py
from django.db.models import Q
from django_rls.policies import ModelPolicy, RLS

class ERPDocument(RLSModel):
    # ... fields ...

    class Meta:
        rls_policies = [
            # Basic Isolation: Document Dept == User Dept
            ModelPolicy(
                'department_isolation',
                filters=Q(department=RLS.tenant_id())
            )
        ]
```

### 3. The Result

Now, your view becomes:

```python
# views.py (The RLS Way)
def document_list(request):
    # SAFE! automatically filtered by the DB
    docs = ERPDocument.objects.all()
    return render(request, 'list.html', {'docs': docs})
```

Even if you write `ERPDocument.objects.all()` in the Django shell, API, or Admin, the database will silently rewrite it to:

```sql
SELECT * FROM myapp_erpdocument
WHERE department_id = current_setting('rls.tenant_id')::integer;
```

The data leakage vector is eliminated at the source.
