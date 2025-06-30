# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django RLS is a Django package that provides PostgreSQL Row Level Security (RLS) capabilities at the database level. It follows Django REST Framework's extensibility patterns and provides true database-level security rather than application-layer filtering.

## Development Setup & Commands

### Initial Setup
```bash
# Install Poetry (dependency management)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Setup pre-commit hooks
poetry run pre-commit install

# Setup development database (PostgreSQL required)
createdb django_rls_dev
```

### Common Development Commands
```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=django_rls --cov-report=term-missing

# Run specific test file
poetry run pytest tests/test_models.py

# Run tests matching pattern
poetry run pytest -k "test_tenant_policy"

# Linting and formatting
poetry run black .
poetry run isort .
poetry run flake8 .
poetry run mypy django_rls

# Run all quality checks
poetry run black . && poetry run isort . && poetry run flake8 . && poetry run mypy django_rls

# Build package
poetry build

# Run Django management commands
poetry run python manage.py enable_rls
poetry run python manage.py disable_rls
```

### Documentation Commands
```bash
# Navigate to docs directory
cd documentations/

# Install documentation dependencies
npm install

# Start documentation server
npm start

# Build documentation
npm run build
```

## Architecture Overview

### Core Components

1. **RLSModel** (`django_rls/models.py`)
   - Base model class that all RLS-enabled models inherit from
   - Uses metaclass `RLSModelMeta` to process policies at model creation
   - Provides `enable_rls()` and `disable_rls()` class methods
   - Automatically enables RLS after migrations via signal

2. **Policy System** (`django_rls/policies.py`)
   - `BasePolicy`: Abstract base class for all policies
   - `TenantPolicy`: Multi-tenant filtering based on tenant field
   - `UserPolicy`: User-based filtering
   - `CustomPolicy`: Allows custom SQL expressions
   - Policies generate PostgreSQL RLS SQL expressions

3. **RLSContextMiddleware** (`django_rls/middleware.py`)
   - Sets PostgreSQL session variables (`rls.user_id`, `rls.tenant_id`)
   - Integrates with Django's request/response cycle
   - Clears context after request processing
   - Supports multiple tenant detection strategies

4. **Database Backend** (`django_rls/backends/postgresql.py`)
   - `RLSDatabaseSchemaEditor`: Custom schema editor for RLS operations
   - `DatabaseWrapper`: Custom database wrapper using the RLS schema editor
   - Follows Django's database backend patterns for proper SQL generation

5. **Management Commands** (`django_rls/management/commands/`)
   - `enable_rls`: Enable RLS for all or specific models
   - `disable_rls`: Disable RLS for all or specific models

### Key Design Patterns

1. **Metaclass Processing**: Policies are validated and attached to models at class creation time
2. **Schema Editor Integration**: RLS operations use Django's schema editor pattern for database abstraction
3. **Migration Operations**: Custom migration operations (EnableRLS, CreatePolicy) for version control
4. **Context Management**: PostgreSQL session variables managed through database functions
5. **Expression Building**: SQL expressions built using Django-style APIs rather than raw strings

### Database Requirements

- PostgreSQL 9.5+ (for RLS support)
- Superuser or appropriate permissions for:
  - `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
  - `CREATE POLICY`
  - `DROP POLICY`

## Testing Strategy

### Test Structure
```
tests/
├── conftest.py          # Pytest configuration and fixtures
├── test_models.py       # RLSModel tests
├── test_policies.py     # Policy class tests
├── test_middleware.py   # Middleware tests
├── test_schema_editor.py # Schema editor tests
└── testapp/            # Test Django app for integration tests
```

### Key Testing Considerations

1. **Database Requirements**: Tests require PostgreSQL with RLS capabilities
2. **Transaction Isolation**: Use `TransactionTestCase` for RLS operations
3. **Context Testing**: Mock Django request objects for middleware testing
4. **Policy Validation**: Test both valid and invalid policy configurations

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run with database query logging
poetry run pytest --log-cli-level=DEBUG

# Run specific test class
poetry run pytest tests/test_policies.py::TestTenantPolicy
```

## Common Development Tasks

### Adding a New Policy Type

1. Create new policy class in `django_rls/policies.py` inheriting from `BasePolicy`
2. Implement `get_sql_expression()` method
3. Add validation in `validate()` method
4. Write tests in `tests/test_policies.py`
5. Add example usage in `examples/`

### Modifying SQL Generation

1. Edit `django_rls/sql/generators.py`
2. Ensure backward compatibility
3. Update tests in `tests/test_sql_generation.py`
4. Test with actual PostgreSQL database

### Adding Middleware Features

1. Edit `django_rls/middleware.py`
2. Consider performance implications
3. Add context extraction methods as needed
4. Update middleware tests

## Project Structure Reference

```
django-rls/
├── django_rls/              # Main package
│   ├── models.py           # RLSModel and metaclass
│   ├── policies.py         # Policy classes
│   ├── middleware.py       # Context middleware
│   ├── backends/           # Database backends
│   │   └── postgresql.py   # PostgreSQL backend with RLS support
│   ├── db/                # Database utilities
│   │   └── functions.py   # Database functions and context managers
│   ├── expressions.py     # SQL expression builders
│   ├── migration_operations.py  # Django migration operations
│   └── management/        # Django management commands
├── tests/                  # Test suite
├── examples/              # Usage examples
└── documentations/        # Docusaurus documentation
```

## Important Notes

- **License**: BSD 3-Clause License (not MIT as mentioned in some docs)
- **Python Support**: 3.10+ required
- **Django Support**: Django 5.0+ required
- **Database**: PostgreSQL-only (RLS is PostgreSQL-specific feature)
- **Security**: This implements database-level security, not application-level filtering

## Debugging Tips

1. **Enable PostgreSQL Query Logging**: Check actual RLS policies being applied
2. **Test Context Variables**: Use `SELECT current_setting('rls.user_id')` in PostgreSQL
3. **Check Policy Status**: Use `\d+ table_name` in psql to see RLS policies
4. **Migration Issues**: Ensure migrations run with appropriate database permissions