---
sidebar_position: 6
---

# 5. Granular Exceptions (ACLs)

Finally, Requirement 3: **Collaborative Exceptions**.

> Alice from Sales needs to view a specific Engineering specification.

We have a `UserPermission` table for this:
*   `user`: Alice
*   `document_id`: 123 (The Spec)
*   `can_view`: True

## The Approach: Without django-rls

Handling granular permissions usually involves complex joins or pre-fetching.

### 1. Complex Q Objects
```python
# views.py
def document_list(request):
    user = request.user

    # "Get my dept docs OR docs I have permission for"
    return ERPDocument.objects.filter(
        Q(department=user.department) |
        Q(userpermission__user=user, userpermission__can_view=True)
    ).distinct() # Distinct is needed because joins can duplicate rows!
```
*Problem: Easy to mess up the OR logic. Performance hit from `distinct()`.*

### 2. Object-Level Permission Frameworks
Libraries like `django-guardian` are great, but they often require explicitly checking permissions row-by-row (`get_objects_for_user`) or adding significant overhead.

---

## The Approach: With django-rls

We define the Access Control List logic directly on the model.

### 1. The Policy

We want to say: *"Access is allowed IF a UserPermission row exists for me."*

`django-rls` makes this incredibly simple. If you reference a related table in a `Q` object, it automatically converts it into a high-performance `EXISTS` subquery.

:::tip Performance Secret
`EXISTS` subqueries are faster than `JOIN`s for security checks because the database stops scanning as soon as it finds **one** match. It doesn't need to count all rows or retrieve data, just confirm existence.
:::

```python
from django.db.models import Subquery, OuterRef

# Assuming loose coupling (Integer ID) for this example
acl_policy = ModelPolicy(
    'acl_policy',
    filters=Q(
        id__in=Subquery(
            UserPermission.objects.filter(
                user=RLS.user_id(),
                can_view=True
            ).values('document_id')
        )
    )
)
```

### 2. Final Model Assembly

Here is our final, production-ready secure model:

```python
class ERPDocument(RLSModel):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    content = models.TextField()

    class Meta:
        rls_policies = [
            hierarchy_policy,   # 1. Recursive Department Tree
            auditor_policy,     # 2. Email Domain Bypass
            acl_policy          # 3. Granular ACL Exceptions
        ]
```

### 3. How Logic Flows

When **Alice (Sales)** tries to view **Engineering Spec (ID 99)**:

1.  **Hierarchy Check**: `Sales` part of `Engineering` tree? **NO**.
2.  **Auditor Check**: Email ends in `@audit`? **NO**.
3.  **ACL Check**: Does `UserPermission` exist for Alice + Doc 99?
    *   Query: `SELECT 1 FROM UserPermission WHERE user_id=Alice AND document_id=99`
    *   Result: **YES**.

**Access Granted.**

Note that PostgreSQL optimizes `EXISTS` checks efficiently. It stops scanning the permission table as soon as it finds *one* match.
