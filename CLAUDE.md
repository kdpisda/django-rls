# Django RLS Development Guide

## Project Overview
Django RLS is a comprehensive Django package that implements PostgreSQL Row Level Security (RLS) for Django applications. It provides a declarative way to add row-level security policies to Django models, similar to how Django REST Framework handles serializers and viewsets.

## Key Components

### 1. Models (`django_rls/models.py`)
- **RLSModel**: Base model class that all RLS-enabled models should inherit from
- **RLSModelMeta**: Metaclass that processes `rls_policies` from model Meta class
- Automatically enables RLS on PostgreSQL tables during migrations

### 2. Policies (`django_rls/policies.py`)
- **BasePolicy**: Abstract base class for all policies
- **TenantPolicy**: Multi-tenant filtering based on tenant field
- **UserPolicy**: User-based access control
- **CustomPolicy**: Flexible custom SQL expressions
- All policies include field name validation to prevent SQL injection

### 3. Middleware (`django_rls/middleware.py`)
- **RLSContextMiddleware**: Sets PostgreSQL session variables for RLS
- Extracts user_id and tenant_id from request
- Clears context after request processing

### 4. Database Backend (`django_rls/backends/postgresql.py`)
- **RLSDatabaseSchemaEditor**: Custom schema editor for RLS operations
- Implements methods: `enable_rls()`, `disable_rls()`, `force_rls()`, `create_policy()`, `drop_policy()`, `alter_policy()`
- Uses Django's schema editor pattern (no manual SQL string construction)

### 5. Migration Operations (`django_rls/migration_operations.py`)
- Custom Django migration operations for RLS
- **EnableRLS**, **DisableRLS**, **CreatePolicy**, **DropPolicy**, **AlterPolicy**

## Testing

### Running Tests
```bash
# Using Poetry (recommended)
poetry run pytest

# Using runtests.py (DRF-style)
poetry run python runtests.py

# Run with coverage
poetry run pytest --cov=django_rls --cov-report=term-missing

# Run PostgreSQL-specific tests
poetry run pytest --postgresql

# Run specific test file
poetry run pytest tests/test_models.py -xvs
```

### Test Structure
Tests follow Django REST Framework patterns:
- `tests/models.py` - Test models used across test suite
- `tests/settings.py` - Test Django settings
- `runtests.py` - Test runner script
- `conftest.py` - Pytest configuration and fixtures

### Docker Testing
```bash
# Start PostgreSQL for testing
make test-db-up

# Run tests with PostgreSQL
make test-postgres

# Clean up
make test-db-down
```

## Development Workflow

### 1. Setting Up Development Environment
```bash
# Clone repository
git clone https://github.com/kdpisda/django-rls.git
cd django-rls

# Install dependencies
poetry install

# Start PostgreSQL (optional, for integration tests)
docker-compose up -d
```

### 2. Making Changes
- Always run tests before committing
- Follow existing code patterns (especially Django REST Framework style)
- Add tests for new features
- Update documentation as needed

### 3. Code Quality
```bash
# Run linting
poetry run flake8 django_rls/

# Run type checking
poetry run mypy django_rls/

# Format code
poetry run black django_rls/ tests/
poetry run isort django_rls/ tests/
```

### 4. Security Considerations
- All field names in policies are validated against SQL injection
- Policy names and table names are properly quoted using Django's `quote_name`
- Custom expressions in `CustomPolicy` should be carefully reviewed
- Context values are parameterized to prevent injection

## Common Issues and Solutions

### 1. Circular Import with BasePolicy
**Problem**: `NameError: name 'BasePolicy' is not defined` in type hints
**Solution**: Use `TYPE_CHECKING` pattern:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from django_rls.policies import BasePolicy
```

### 2. Django Meta Class Compatibility
**Problem**: `TypeError: 'class Meta' got invalid attribute(s): rls_policies`
**Solution**: Extract `rls_policies` in metaclass before Django processes Meta:
```python
class RLSModelMeta(models.base.ModelBase):
    def __new__(cls, name, bases, namespace, **kwargs):
        meta = namespace.get('Meta')
        if meta and hasattr(meta, 'rls_policies'):
            rls_policies = getattr(meta, 'rls_policies', [])
            delattr(meta, 'rls_policies')  # Remove before Django sees it
```

### 3. Test Database Access
**Problem**: `RuntimeError: Database access not allowed`
**Solution**: Add `@pytest.mark.django_db` decorator or inherit from `django.test.TestCase`

### 4. PostgreSQL-specific Functions in Tests
**Problem**: `sqlite3.OperationalError: no such function: set_config`
**Solution**: Mock the database-specific functions in tests:
```python
@patch('django_rls.db.functions.set_rls_context')
def test_something(self, mock_set_rls_context):
    # Test code here
```

## Architecture Decisions

### 1. Schema Editor Pattern
Instead of manual SQL string construction, we use Django's schema editor pattern:
- Safer and more maintainable
- Properly handles quoting and escaping
- Consistent with Django's approach

### 2. Policy Validation
All policies validate field names to prevent SQL injection:
- Only alphanumeric characters and underscores allowed
- Must start with letter or underscore
- Raises `PolicyError` for invalid names

### 3. Testing Strategy
Following Django REST Framework's testing approach:
- Separate test models in `tests/models.py`
- Custom test runner in `runtests.py`
- Comprehensive fixture support in `conftest.py`
- Clear separation between unit and integration tests

## Future Enhancements

1. **Additional Policy Types**
   - TimeBasedPolicy for temporal access control
   - GroupPolicy for group-based permissions
   - RolePolicy for role-based access control

2. **Performance Optimizations**
   - Policy caching mechanisms
   - Batch policy operations
   - Query optimization helpers

3. **Management Commands**
   - `manage.py rls_audit` - Audit current RLS policies
   - `manage.py rls_sync` - Sync policies with database
   - `manage.py rls_test` - Test policy effectiveness

4. **Admin Integration**
   - Django Admin interface for policy management
   - Visual policy editor
   - Policy testing interface

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run full test suite
5. Submit pull request

Please ensure:
- All tests pass
- Code follows project style
- Documentation is updated
- Security implications are considered