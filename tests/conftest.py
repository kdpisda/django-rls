"""
Pytest configuration for Django RLS tests.

Based on Django REST Framework's testing patterns.
"""
import os
import pytest
from django.conf import settings


def pytest_configure(config):
    """Configure pytest with Django settings."""
    import sys
    import os
    
    # Add project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from django.conf import settings
    
    # Configure Django if not already configured
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
        
        import django
        django.setup()


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--postgresql",
        action="store_true",
        default=False,
        help="Run tests with PostgreSQL backend"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    # Add postgresql marker to tests that require it
    if not config.getoption("--postgresql"):
        skip_postgresql = pytest.mark.skip(reason="PostgreSQL not enabled (use --postgresql)")
        for item in items:
            if "postgresql" in item.keywords:
                item.add_marker(skip_postgresql)


# Fixtures
@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Override Django's database setup."""
    # This runs after Django's default db setup
    pass


@pytest.fixture
def api_client():
    """Provide a test client."""
    from django.test import Client
    return Client()


@pytest.fixture
def user(db):
    """Create a test user."""
    from django.contrib.auth.models import User
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Provide an authenticated test client."""
    api_client.force_login(user)
    return api_client


# Test markers
pytest.mark.postgresql = pytest.mark.postgresql
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow