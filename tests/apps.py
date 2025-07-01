"""App configuration for tests."""

from django.apps import AppConfig


class TestsConfig(AppConfig):
    """Configuration for the tests app."""
    name = 'tests'
    default_auto_field = 'django.db.models.BigAutoField'