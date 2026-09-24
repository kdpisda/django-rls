---
sidebar_position: 4
---

# Testing

Testing RLS-enabled models requires **real PostgreSQL**. Policies are enforced at the database level — SQLite and mocked connections do not exercise RLS.

## Running the test suite

```bash
make test              # starts docker compose Postgres, runs full suite
make test-security     # security regression tests only
make test-cov          # with coverage
```

See [Local Testing](../contributing/local_testing) for `scripts/run-tests.sh`, environment variables, and troubleshooting.

## Basic testing setup (1.0.0+)

Use `system_rls_context()` when switching identity. Identity keys are immutable once set unless you use a privileged scope.

```python
from django.test import TestCase
from django.contrib.auth.models import User
from django_rls.context import system_rls_context, set_rls_context
from myapp.models import Document

class RLSTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('user1')
        self.user2 = User.objects.create_user('user2')

        with system_rls_context(user_id=self.user1.id):
            self.doc1 = Document.objects.create(
                title='User 1 Doc',
                owner=self.user1
            )

        with system_rls_context(user_id=self.user2.id):
            self.doc2 = Document.objects.create(
                title='User 2 Doc',
                owner=self.user2
            )
```

## Testing Policy Enforcement

```python
def test_user_can_only_see_own_documents(self):
    with system_rls_context(user_id=self.user1.id):
    
        docs = Document.objects.all()
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs.first().owner, self.user1)

    with system_rls_context(user_id=self.user2.id):
        docs = Document.objects.all()
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs.first().owner, self.user2)

def test_user_cannot_update_others_documents(self):
    with system_rls_context(user_id=self.user1.id):
    
        updated = Document.objects.filter(id=self.doc2.id).update(title='Hacked!')
        self.assertEqual(updated, 0)

    self.doc2.refresh_from_db()
    self.assertEqual(self.doc2.title, 'User 2 Doc')
```

## Test Utilities

Django RLS provides test utilities to make testing easier:

```python
from django_rls.test import RLSTestMixin

class DocumentTestCase(RLSTestMixin, TestCase):
    def test_with_rls_disabled(self):
        # Temporarily disable RLS
        with self.disable_rls(Document):
            # Can see all documents
            docs = Document.objects.all()
            self.assertEqual(docs.count(), 2)
    
    def test_as_different_user(self):
        # Test as user1
        with self.as_user(self.user1):
            docs = Document.objects.all()
            self.assertEqual(docs.count(), 1)
        
        # Test as user2
        with self.as_user(self.user2):
            docs = Document.objects.all()
            self.assertEqual(docs.count(), 1)
```

## Testing Multi-Tenant Applications

```python
class TenantTestCase(RLSTestMixin, TestCase):
    def setUp(self):
        # Create tenants
        self.tenant1 = Tenant.objects.create(name='Tenant 1')
        self.tenant2 = Tenant.objects.create(name='Tenant 2')
        
        # Create users in different tenants
        self.user1 = User.objects.create_user('user1')
        self.user1.profile.tenant = self.tenant1
        self.user1.profile.save()
        
    def test_tenant_isolation(self):
        # Set context for tenant1
        with self.with_context(user_id=self.user1.id, 
                              tenant_id=self.tenant1.id):
            # Create data in tenant1
            TenantModel.objects.create(
                name='Tenant 1 Data',
                tenant=self.tenant1
            )
        
        # Switch to tenant2
        with self.with_context(user_id=self.user2.id,
                              tenant_id=self.tenant2.id):
            # Should not see tenant1's data
            data = TenantModel.objects.all()
            self.assertEqual(data.count(), 0)
```

## Testing with Fixtures

```python
# fixtures/test_rls_data.json
[
    {
        "model": "myapp.document",
        "pk": 1,
        "fields": {
            "title": "Public Document",
            "is_public": true,
            "owner": 1
        }
    }
]

class FixtureTestCase(TestCase):
    fixtures = ['test_rls_data.json']
    
    def test_fixtures_respect_rls(self):
        # Set context
        set_rls_context('user_id', '1')
        
        # Verify fixture data is filtered
        docs = Document.objects.all()
        # Only see documents based on policy
```

## Testing Custom Policies

```python
def test_complex_policy(self):
    # Create test data
    project = Project.objects.create(
        name='Test Project',
        owner=self.user1,
        is_public=False,
        tenant=self.tenant1
    )
    project.team.add(self.user2)
    
    # Test owner access
    with self.as_user(self.user1, tenant=self.tenant1):
        projects = Project.objects.all()
        self.assertIn(project, projects)
    
    # Test team member access
    with self.as_user(self.user2, tenant=self.tenant1):
        projects = Project.objects.all()
        self.assertIn(project, projects)
    
    # Test no access from different tenant
    with self.as_user(self.user3, tenant=self.tenant2):
        projects = Project.objects.all()
        self.assertNotIn(project, projects)
```

## Performance Testing

```python
from django.test import TransactionTestCase
from django.test.utils import override_settings
import time

class RLSPerformanceTest(TransactionTestCase):
    def test_query_performance_with_rls(self):
        # Create large dataset
        for i in range(1000):
            Document.objects.create(
                title=f'Doc {i}',
                owner=self.user1 if i % 2 == 0 else self.user2
            )
        
        # Test query time with RLS
        set_rls_context('user_id', self.user1.id)
        
        start = time.time()
        docs = list(Document.objects.all())
        rls_time = time.time() - start
        
        self.assertEqual(len(docs), 500)  # Half the documents
        self.assertLess(rls_time, 0.1)  # Should be fast
```

## Security regression tests

The `tests/security/` package runs against live PostgreSQL and verifies SQL injection resistance, identity immutability, middleware trust boundaries, and connection hygiene. Run via:

```bash
make test-security
```

Prefer asserting `get_rls_context()` round-trips over mocking `django_rls.context.connection`.

## CI/CD testing

GitHub Actions runs the full `pytest` tree against PostgreSQL 17 on every PR:

```yaml
- name: Run tests with PostgreSQL
  run: poetry run pytest -xvs --cov=django_rls
  env:
    USE_POSTGRESQL: "true"
    DB_HOST: localhost
    DB_PORT: 5432
    DB_USER: rls_test_user
    DB_PASSWORD: testpass
```

Locally, `make test` mirrors this using docker compose on port 5433.

## Best Practices

1. **Always set context** before running queries in tests
2. **Test policy edge cases** (empty results, no access, etc.)
3. **Use transactions** to isolate test data
4. **Test with production-like data** volumes
5. **Verify both positive and negative** cases
6. **Test policy combinations** if using multiple policies

## Common Testing Patterns

### Factory Pattern

```python
import factory
from django_rls.test import RLSFactory

class DocumentFactory(RLSFactory):
    class Meta:
        model = Document
    
    title = factory.Faker('sentence')
    owner = factory.SubFactory(UserFactory)
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Automatically set RLS context from owner
        owner = kwargs.get('owner')
        if owner:
            set_rls_context('user_id', owner.id)
        return super()._create(model_class, *args, **kwargs)
```

### Pytest Fixtures

```python
import pytest
from django_rls.db.functions import set_rls_context

@pytest.fixture
def user_context(user):
    """Set RLS context for a user."""
    set_rls_context('user_id', user.id)
    yield user
    # Cleanup if needed

@pytest.mark.django_db
def test_document_list(user_context, client):
    response = client.get('/documents/')
    assert response.status_code == 200
```