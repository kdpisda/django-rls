"""Example Django settings for using Django RLS."""

# ... other settings ...

DATABASES = {
    "default": {
        # Use our custom PostgreSQL backend that supports RLS operations
        "ENGINE": "django_rls.backends.postgresql",
        "NAME": "your_database",
        "USER": "your_user",
        "PASSWORD": "your_password",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

INSTALLED_APPS = [
    # ... other apps ...
    "django_rls",
]

MIDDLEWARE = [
    # ... other middleware ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Add RLS middleware after authentication
    "django_rls.middleware.RLSContextMiddleware",
]

# Optional: Configure RLS behavior
DJANGO_RLS = {
    "AUTO_ENABLE_RLS": True,
    "STRICT_MIGRATE_RLS": True,  # Fail migrations if RLS enablement fails
    "DEFAULT_ROLES": "authenticated",  # Prefer app-specific DB role over 'public'
    "DEFAULT_PERMISSIVE": True,
    "REQUIRE_CONTEXT": True,  # Raise if identity context missing on RLS queries
    "ALLOW_SESSION_TENANT": False,  # Never trust session tenant_id without validation
    "TENANT_MEMBERSHIP_VALIDATOR": "myapp.rls.validate_tenant_membership",
    "REGISTERED_CONTEXT_KEYS": ["user_email", "department_id"],
    "RESET_CONTEXT_ON_CONNECT": True,
    "AUDIT_LOG": True,
    "CONTEXT_EXTRACTORS": [
        "myapp.rls.extract_tenant_from_subdomain",
        "myapp.rls.extract_user_organization",
    ],
    "DEBUG": False,
}
