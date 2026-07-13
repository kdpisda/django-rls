"""Custom exceptions for Django RLS."""


class RLSError(Exception):
    """Base exception for RLS-related errors."""

    pass


class PolicyError(RLSError):
    """Exception raised for policy-related errors."""

    pass


class BackendError(RLSError):
    """Exception raised for backend-related errors."""

    pass


class ConfigurationError(RLSError):
    """Exception raised for configuration errors."""

    pass


class RLSContextImmutableError(RLSError):
    """Raised when protected identity context cannot be overridden."""


class RLSContextRequiredError(RLSError):
    """Raised when required RLS identity context is missing."""


class TenantAccessDeniedError(RLSError):
    """Raised when tenant context fails membership validation."""
