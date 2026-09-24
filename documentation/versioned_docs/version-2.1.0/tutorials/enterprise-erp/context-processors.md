---
sidebar_position: 5
---

# 4. Dynamic Context Processors

We now have Requirement 4: **The Auditor Role**.

> Anyone logging in with an email ending in `@audit.megacorp.com` must have read-only access to EVERYTHING.

This attribute (email domain) isn't strictly foreign key data. It's a property of the user session.

## The Approach: Without django-rls

To implement a "Global Override" like this, you usually pollute your codebase with `if` statements.

### 1. The "View Logic" Spaghetti
```python
# views.py
def document_list(request):
    queryset = ERPDocument.objects.all()

    # "Oh wait, check if they are an auditor"
    if request.user.email.endswith('@audit.megacorp.com'):
        return queryset

    # "Else, apply normal filters"
    return queryset.filter(department=request.user.department)
```
*Problem: You have to repeat this `if/else` logic in every single view.*

### 2. Custom Managers / Mixins
You might encapsulate this in a custom Manager.
```python
class DocumentManager(models.Manager):
    def for_user(self, user):
        if user.email.endswith('@audit.megacorp.com'):
            return self.all()
        return self.filter(department=user.department)
```
*Problem: Developers might forget and call `.objects.all()` instead of `.objects.for_user(user)`.*

---

## The Approach: With django-rls

We treat the email domain as a **Context Fact** in the database.

### 1. Injecting the Fact (Context Processor)

Just like you pass variables to Django Templates, we pass variables to the Database Session.

Create `myapp/context.py`:
```python
def audit_context(request):
    if request.user.is_authenticated:
        return {
            'user_email': request.user.email
        }
    return {}
```

Register in `settings.py`:
```python
RLS_CONTEXT_PROCESSORS = [
    'myapp.context.audit_context'
]
```

### 2. The Policy

### Approach A: The Pythonic Way (Recommended)

:::tip Best Practice
Always prefer **ModelPolicy** with Django `Q` objects. It is database-agnostic, easier to read, and less prone to SQL injection errors than raw SQL strings.
:::

Using `ModelPolicy` and `RLS.context()`:

```python
from django.db.models import Q, CharField
from django_rls.policies import ModelPolicy, RLS

auditor_policy = ModelPolicy(
    'auditor_access',
    # Logic: OR if email ends with ...
    filters=Q(user_email__endswith='@audit.megacorp.com'),
    annotations={
        # Map the lookup 'user_email' to the RLS context variable
        'user_email': RLS.context('user_email', output_field=CharField())
    }
)
```

### 3. Combining Policies

`django-rls` operates on a **Permissive (OR)** basis by default.

```python
class ERPDocument(RLSModel):
    # ...
    class Meta:
        rls_policies = [
            hierarchy_policy,   # Policy 1: Dept Access
            auditor_policy      # Policy 2: Auditor Override
        ]
```

### The Result

When **Bob the Auditor** queries `ERPDocument.objects.all()`:

1.  Policy 1 (Hierarchy) **FAILS** (He's not in Engineering).
2.  Policy 2 (Auditor) **PASSES** (His email matches context).
3.  **Access Granted**.

All without writing a single `if` statement in your views.
