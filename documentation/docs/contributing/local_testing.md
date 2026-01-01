# Local Testing Guide for Django RLS

## Prerequisites

### Option 1: Using Docker (Recommended)
1. **Docker and Docker Compose**
   ```bash
   # Install Docker Desktop from https://www.docker.com/products/docker-desktop
   # Or via package manager:
   
   # macOS
   brew install --cask docker
   
   # Ubuntu
   sudo apt-get install docker.io docker-compose
   sudo usermod -aG docker $USER
   ```

2. **Poetry** for dependency management
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

### Option 2: Local PostgreSQL Installation
1. **PostgreSQL** must be installed and running
   ```bash
   # macOS
   brew install postgresql
   brew services start postgresql

   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   sudo systemctl start postgresql

   # Arch Linux
   sudo pacman -S postgresql
   sudo systemctl start postgresql
   ```

2. **Poetry** for dependency management
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

## Quick Start with Docker

### 1. Start PostgreSQL with Docker
```bash
# Start PostgreSQL (runs on port 5432)
make docker-up

# Or using docker-compose directly
docker-compose up -d
```

### 2. Install Dependencies
```bash
make install
# Or: poetry install
```

### 3. Run Tests
```bash
# Using Make (Recommended)
make test              # Run all tests
make test-cov         # Run with coverage
make test-security    # Run security tests only
```

## Quick Start without Docker

### 1. Install Dependencies
```bash
poetry install
```

### 2. Create Test Database
```bash
createdb test_django_rls
```

### 3. Run Tests

#### Manual Commands

```bash
# Activate virtual environment
poetry shell

# Run all tests
pytest
```

## Environment Variables

```bash
# Set database URL (if not using default)
export DATABASE_URL="postgres://user:password@localhost:5432/test_django_rls"

# Run tests with custom database
DATABASE_URL="postgres://localhost/mydb" pytest
```

## Useful Testing Commands

### Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov=django_rls --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Test Debugging
```bash
# Run with print statements visible
pytest -s

# Drop into debugger on failure
pytest --pdb

# Run only failed tests from last run
pytest --lf

# Run failed tests first, then others
pytest --ff
```

### Linting and Code Quality
```bash
# Run all quality checks
poetry run black --check .
poetry run isort --check-only .
poetry run flake8 .
poetry run mypy django_rls

# Auto-fix formatting
poetry run black .
poetry run isort .
```

## Testing Best Practices

1. **Always test with PostgreSQL** - SQLite doesn't support RLS
2. **Use transactions** - Tests should be isolated
3. **Mock external dependencies** - Don't rely on external services
4. **Test security thoroughly** - Run security tests before releases

## Docker Commands Reference

```bash
# Start services
make docker-up          # Start PostgreSQL
make docker-test-up     # Start lightweight test PostgreSQL (port 5433)

# Stop services  
make docker-down        # Stop PostgreSQL
make docker-test-down   # Stop test PostgreSQL

# Database management
make db-shell          # Open PostgreSQL shell
make db-reset          # Reset test database

# View logs
make docker-logs       # Show PostgreSQL logs

# Run tests with Docker
make test-docker       # Run tests with test PostgreSQL container

# Full CI simulation locally
make ci-local          # Run linting, type checking, and all tests
```

## Troubleshooting

### Docker PostgreSQL Connection Issues
```bash
# Check if containers are running
docker ps

# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Reset everything
make docker-reset
```

### Local PostgreSQL Connection Issues
```bash
# Check PostgreSQL is running
pg_isready

# Check you can connect
psql -U postgres -c "SELECT version();"

# Create test database with specific user
createdb -U postgres test_django_rls
```

### Permission Issues
```bash
# Grant permissions to your user
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE test_django_rls TO $USER;"
```

### Clean Test Environment
```bash
# Drop and recreate test database
dropdb test_django_rls
createdb test_django_rls

# Clear pytest cache
pytest --cache-clear

# Remove coverage data
rm -rf .coverage htmlcov/
```

## Continuous Integration

The same tests run in GitHub Actions on:
- Python 3.10, 3.11, 3.12
- Django 5.0, 5.1
- PostgreSQL 15

Make sure your tests pass locally before pushing!