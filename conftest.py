"""Pytest configuration for django-rls tests."""

import os
import sys
import django
from django.conf import settings

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