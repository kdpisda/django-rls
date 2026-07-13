"""Pytest configuration for django-rls tests."""

import os
import sys

import django
import pytest
from django.conf import settings
from django.db import connection

from django_rls.context import clear_rls_context

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def pytest_configure(config):
    """Configure Django settings for tests."""
    if not settings.configured:
        from tests import settings as test_settings
        
        settings.configure(
            **{
                key: getattr(test_settings, key)
                for key in dir(test_settings)
                if not key.startswith('_')
            }
        )
        
        # Setup Django
        django.setup()
        
        # Ensure all apps are loaded properly
        from django.apps import apps
        apps.check_apps_ready()


@pytest.fixture
def require_postgresql():
    """Skip when the active database is not PostgreSQL."""
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL required")


@pytest.fixture(autouse=True)
def _cleanup_rls_db_context():
    """Reset RLS session variables on the live connection after DB-backed tests."""
    yield
    if connection.vendor != "postgresql":
        return
    try:
        clear_rls_context()
    except Exception:
        # SimpleTestCase and other non-DB tests must not trigger queries here.
        pass