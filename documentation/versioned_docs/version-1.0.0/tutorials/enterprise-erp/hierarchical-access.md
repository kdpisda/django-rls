---
sidebar_position: 4
---

# 3. Hierarchical Permissions (Recursive)

MegaCorp has a nested structure.

*   Engineering
    *   Backend
    *   Frontend

**The Rule**: The VP of Engineering (who belongs to the "Engineering" dept) must see documents from "Backend" and "Frontend".

## The Approach: Without django-rls

This is notoriously difficult in standard Django.

### Option 1: The "Recursive Loop" (Performance Killer)
To get all documents for a manager, you have to find all sub-departments first.

```python
def get_all_sub_departments(dept):
    ids = [dept.id]
    for child in dept.sub_departments.all():
        ids.extend(get_all_sub_departments(child))
    return ids

# views.py
def document_list(request):
    user_dept = request.user.profile.department

    # PROBLEM: This executes dozens of SQL queries just to build the list!
    visible_dept_ids = get_all_sub_departments(user_dept)

    return ERPDocument.objects.filter(department_id__in=visible_dept_ids)
```

### Option 2: The "Materialized Path" (Maintenance Nightmare)
You might store a `path` string (e.g., `/1/2/3/`) on each department.
*   **Pros**: Fast querying (`startswith`).
*   **Cons**: Moving a department requires updating thousands of rows.

---

## The Approach: With django-rls

We solve this problem **once**, using the power of PostgreSQL **Common Table Expressions (CTEs)**. This allows the database to traverse the tree efficiently in a single query.

:::info Why Raw SQL?
For recursive tree traversal, standard Django ORM expressions are not expressive enough. A Recursive CTE is the **industry standard** "Best Way" to solve this problem for performance, turning 50 potential queries into 1.
:::

### 1. Defining the Policy

We write a `CustomPolicy` using SQL recursion.

```python
from django_rls.policies import CustomPolicy

# "Allow if the document's department is in the tree of my department"
hierarchy_policy = CustomPolicy(
    'hierarchy_policy',
    expression="""
        department_id IN (
            WITH RECURSIVE dept_tree AS (
                -- Anchor: Start with the user's current department
                SELECT id FROM myapp_department
                WHERE id = current_setting('rls.tenant_id')::integer

                UNION ALL

                -- Recursive: Find children of the departments we've found so far
                SELECT d.id FROM myapp_department d
                INNER JOIN dept_tree dt ON d.parent_id = dt.id
            )
            SELECT id FROM dept_tree
        )
    """
)
```

### 2. Updating the Model

Update `ERPDocument` to use this new policy *instead* of the simple one.

```python
class ERPDocument(RLSModel):
    # ... fields

    class Meta:
        rls_policies = [
            hierarchy_policy
        ]
```

### 3. The Result

Now, when the VP of Engineering logs in:

```python
# View code remains deceptively simple!
documents = ERPDocument.objects.all()
```

PostgreSQL automatically:
1.  Takes the user's department ID.
2.  Recursively finds all 50 sub-departments in milliseconds.
3.  Returns only the matching documents.

No Python loops. No N+1 query problems. No risk of forgetting a child department.
