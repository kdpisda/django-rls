---
sidebar_position: 7
---

# 6. Verification & Testing

Security code without tests is just a hopeful suggestion. `django-rls` provides tools to specifically test your RLS policies.

## Manual verification via Django Shell

You can verify policies interactively:

```bash
python manage.py shell
```

```python
from myapp.models import ERPDocument, Department
from django.contrib.auth.models import User
from django_rls.db.functions import set_rls_context

# Setup
eng = Department.objects.get(name='Engineering')
sales = Department.objects.get(name='Sales')
alice = User.objects.get(username='alice') # Sales

# Create an Engineering Doc
doc = ERPDocument.objects.create(title="Top Secret", department=eng)

# 1. Simulate Alice (Sales)
set_rls_context('user_id', alice.id)
set_rls_context('tenant_id', sales.id)

print(ERPDocument.objects.count())
# Output: 0 (Correct! Hidden)

# 2. Simulate Bob (Engineering VP)
bob = User.objects.create(username='bob')
set_rls_context('user_id', bob.id)
set_rls_context('tenant_id', eng.id)

print(ERPDocument.objects.count())
# Output: 1 (Visible!)
```

## Automated Testing

Use the `RLSTestMixin` in your Django tests.

```python
from django.test import TestCase
from django_rls.test import RLSTestMixin

class SecurityTest(RLSTestMixin, TestCase):
    def test_isolation(self):
        # Create data...

        # Helper context manager
        with self.with_context(user_id=self.alice.id, tenant_id=self.sales_dept.id):
             self.assertFalse(ERPDocument.objects.exists())

    def test_auditor_access(self):
        # Simulate Context Processor injection manually for test
        # Or rely on integration test if using Client()

        # Test direct context:
        with self.with_context(user_email='audit@audit.megacorp.com'):
            self.assertTrue(ERPDocument.objects.exists())
```

> **Note**: `django-rls` tests require a PostgreSQL database. They will not work with SQLite.
