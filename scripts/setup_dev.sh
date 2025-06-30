#!/bin/bash
# Development setup script for Django RLS

echo "Setting up Django RLS development environment..."

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is not installed. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install dependencies
echo "Installing dependencies..."
poetry install

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
poetry run pre-commit install

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "WARNING: PostgreSQL client not found. Please install PostgreSQL."
else
    echo "Creating test database..."
    createdb django_rls_dev 2>/dev/null || echo "Database may already exist"
fi

# Run initial tests
echo "Running tests..."
poetry run pytest tests/test_policies.py -v

echo "Setup complete! You can now start developing."
echo ""
echo "Common commands:"
echo "  poetry run pytest          - Run tests"
echo "  poetry run black .         - Format code"
echo "  poetry run flake8 .        - Lint code"
echo "  poetry shell               - Activate virtual environment"