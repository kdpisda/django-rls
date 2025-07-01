"""Test that Django apps are configured correctly."""

from django.test import TestCase
from django.apps import apps


class TestAppsConfiguration(TestCase):
    """Test Django apps configuration."""
    
    def test_auth_app_is_installed(self):
        """Ensure django.contrib.auth is installed."""
        self.assertIn('auth', apps.all_models)
    
    def test_django_rls_app_is_installed(self):
        """Ensure django_rls is installed."""
        self.assertIn('django_rls', apps.all_models)
    
    def test_tests_app_is_installed(self):
        """Ensure tests app is installed."""
        self.assertIn('tests', apps.all_models)
    
    def test_auth_user_model_exists(self):
        """Ensure User model is available."""
        from django.contrib.auth.models import User
        self.assertTrue(User._meta.db_table)