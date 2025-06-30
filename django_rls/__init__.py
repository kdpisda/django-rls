"""
Django RLS - PostgreSQL Row Level Security for Django
"""

from .__version__ import __version__, __version_info__

__author__ = "Kuldeep Pisda"
__email__ = "kdpisda@gmail.com"

default_app_config = "django_rls.apps.DjangoRLSConfig"

# Define what's available for import
__all__ = [
    "__version__",
    "__version_info__",
    "RLSModel",
    "BasePolicy",
    "TenantPolicy",
    "UserPolicy",
]


# Lazy imports to avoid Django app registry issues
def __getattr__(name):
    """Lazy import of components to avoid circular imports and app registry issues."""
    if name == "RLSModel":
        from .models import RLSModel
        return RLSModel
    elif name == "BasePolicy":
        from .policies import BasePolicy
        return BasePolicy
    elif name == "TenantPolicy":
        from .policies import TenantPolicy
        return TenantPolicy
    elif name == "UserPolicy":
        from .policies import UserPolicy
        return UserPolicy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")