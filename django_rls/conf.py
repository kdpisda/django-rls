"""Configuration for Django RLS."""

from django.conf import settings


class RLSConfig:
    """Configuration holder for Django RLS."""

    def _settings(self) -> dict:
        return getattr(settings, "DJANGO_RLS", {})

    @property
    def auto_enable_rls(self):
        """Whether to automatically enable RLS after migrations."""
        return self._settings().get("AUTO_ENABLE_RLS", True)

    @property
    def strict_migrate_rls(self):
        """Re-raise when post_migrate RLS enablement fails."""
        return self._settings().get("STRICT_MIGRATE_RLS", False)

    @property
    def default_roles(self):
        """Default roles for policies."""
        return self._settings().get("DEFAULT_ROLES", "public")

    @property
    def default_permissive(self):
        """Whether policies are permissive by default."""
        return self._settings().get("DEFAULT_PERMISSIVE", True)

    @property
    def context_extractors(self):
        """List of context extractor functions."""
        return self._settings().get("CONTEXT_EXTRACTORS", [])

    @property
    def debug(self):
        """Enable debug logging."""
        return self._settings().get("DEBUG", False)

    @property
    def audit_log(self):
        """Log RLS context set/clear events (recommended for production audits)."""
        return self._settings().get("AUDIT_LOG", False)

    @property
    def require_context(self):
        """Require user_id or tenant_id before querying RLSModel instances."""
        return self._settings().get("REQUIRE_CONTEXT", False)

    @property
    def allow_session_tenant(self):
        """Allow tenant_id from session (disabled by default — validate membership)."""
        return self._settings().get("ALLOW_SESSION_TENANT", False)

    @property
    def tenant_membership_validator(self):
        """Dotted path to callable(request, tenant_id) -> bool."""
        return self._settings().get("TENANT_MEMBERSHIP_VALIDATOR", None)

    @property
    def registered_context_keys(self):
        """Custom context keys cleared on connection reset (beyond user/tenant)."""
        return self._settings().get("REGISTERED_CONTEXT_KEYS", [])

    @property
    def reset_context_on_connect(self):
        """Clear RLS session variables when a DB connection is established."""
        return self._settings().get("RESET_CONTEXT_ON_CONNECT", True)

    @property
    def use_native_rls(self):
        """Whether to use native PostgreSQL RLS (requires custom backend)."""
        db_config = settings.DATABASES.get("default", {})
        return db_config.get("ENGINE") == "django_rls.backends.postgresql"


# Global config instance
rls_config = RLSConfig()
