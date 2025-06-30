"""Configuration for Django RLS."""

from django.conf import settings


class RLSConfig:
    """Configuration holder for Django RLS."""
    
    @property
    def auto_enable_rls(self):
        """Whether to automatically enable RLS after migrations."""
        return getattr(settings, 'DJANGO_RLS', {}).get('AUTO_ENABLE_RLS', True)
    
    @property
    def default_roles(self):
        """Default roles for policies."""
        return getattr(settings, 'DJANGO_RLS', {}).get('DEFAULT_ROLES', 'public')
    
    @property
    def default_permissive(self):
        """Whether policies are permissive by default."""
        return getattr(settings, 'DJANGO_RLS', {}).get('DEFAULT_PERMISSIVE', True)
    
    @property
    def context_extractors(self):
        """List of context extractor functions."""
        return getattr(settings, 'DJANGO_RLS', {}).get('CONTEXT_EXTRACTORS', [])
    
    @property
    def debug(self):
        """Enable debug logging."""
        return getattr(settings, 'DJANGO_RLS', {}).get('DEBUG', False)
    
    @property
    def use_native_rls(self):
        """Whether to use native PostgreSQL RLS (requires custom backend)."""
        # Check if using our custom backend
        db_config = settings.DATABASES.get('default', {})
        return db_config.get('ENGINE') == 'django_rls.backends.postgresql'


# Global config instance
rls_config = RLSConfig()