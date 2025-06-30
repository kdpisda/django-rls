"""Example Django settings for using Django RLS."""

# ... other settings ...

DATABASES = {
    'default': {
        # Use our custom PostgreSQL backend that supports RLS operations
        'ENGINE': 'django_rls.backends.postgresql',
        'NAME': 'your_database',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

INSTALLED_APPS = [
    # ... other apps ...
    'django_rls',
]

MIDDLEWARE = [
    # ... other middleware ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Add RLS middleware after authentication
    'django_rls.middleware.RLSContextMiddleware',
]

# Optional: Configure RLS behavior
DJANGO_RLS = {
    # Automatically enable RLS after migrations
    'AUTO_ENABLE_RLS': True,
    
    # Default roles for policies
    'DEFAULT_ROLES': 'public',
    
    # Whether policies are permissive by default
    'DEFAULT_PERMISSIVE': True,
    
    # Custom context extractors
    'CONTEXT_EXTRACTORS': [
        'myapp.rls.extract_tenant_from_subdomain',
        'myapp.rls.extract_user_organization',
    ],
    
    # Enable debug logging
    'DEBUG': False,
}