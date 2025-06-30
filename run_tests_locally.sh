#!/bin/bash
# Script to run Django RLS tests locally

echo "🧪 Django RLS Test Runner"
echo "========================"
echo ""

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Please install it first:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check if PostgreSQL is available
if command -v docker &> /dev/null; then
    # Check if PostgreSQL is running in Docker
    if docker ps | grep -q "django_rls_postgres"; then
        echo "✅ Using PostgreSQL from Docker"
        export DATABASE_URL="postgres://postgres:postgres@localhost:5432/test_django_rls"
    elif docker ps | grep -q "django_rls_test_postgres"; then
        echo "✅ Using test PostgreSQL from Docker (port 5433)"
        export DATABASE_URL="postgres://postgres:postgres@localhost:5433/test_django_rls"
    else
        echo "⚠️  PostgreSQL not running. Starting with Docker..."
        docker-compose up -d
        sleep 3
        export DATABASE_URL="postgres://postgres:postgres@localhost:5432/test_django_rls"
    fi
elif command -v psql &> /dev/null; then
    echo "✅ Using local PostgreSQL installation"
else
    echo "❌ PostgreSQL not found. Please either:"
    echo "   1. Install Docker and run: docker-compose up -d"
    echo "   2. Install PostgreSQL locally"
    echo "      On macOS: brew install postgresql"
    echo "      On Ubuntu: sudo apt-get install postgresql"
    exit 1
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
    poetry install
fi

# Database URL is already set above based on PostgreSQL detection
echo "🗄️  Database URL: $DATABASE_URL"

echo ""
echo "🚀 Running tests..."
echo ""

# Run tests based on argument
case "$1" in
    "all")
        echo "Running all tests with coverage..."
        poetry run pytest --cov=django_rls --cov-report=term-missing --cov-report=html -v
        ;;
    "security")
        echo "Running security tests only..."
        poetry run pytest tests/test_security.py -v
        ;;
    "fast")
        echo "Running tests without coverage..."
        poetry run pytest -v
        ;;
    "specific")
        if [ -z "$2" ]; then
            echo "Please specify a test file or pattern"
            echo "Example: ./run_tests_locally.sh specific test_policies"
            exit 1
        fi
        echo "Running specific tests: $2"
        poetry run pytest -k "$2" -v
        ;;
    *)
        echo "Usage: ./run_tests_locally.sh [all|security|fast|specific <pattern>]"
        echo ""
        echo "Options:"
        echo "  all      - Run all tests with coverage report"
        echo "  security - Run only security tests"
        echo "  fast     - Run all tests without coverage"
        echo "  specific - Run specific tests matching pattern"
        echo ""
        echo "Examples:"
        echo "  ./run_tests_locally.sh all"
        echo "  ./run_tests_locally.sh security"
        echo "  ./run_tests_locally.sh specific test_tenant_policy"
        echo ""
        echo "Running all tests with coverage by default..."
        poetry run pytest --cov=django_rls --cov-report=term-missing -v
        ;;
esac

# Show coverage report location if it was generated
if [ -d "htmlcov" ]; then
    echo ""
    echo "📊 Coverage report generated: open htmlcov/index.html"
fi