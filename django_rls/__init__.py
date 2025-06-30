"""
Django RLS - PostgreSQL Row Level Security for Django
"""

from .__version__ import __version__, __version_info__

__author__ = "Kuldeep Pisda"
__email__ = "your.email@example.com"

default_app_config = "django_rls.apps.DjangoRLSConfig"

# Export main components
from .models import RLSModel
from .policies import BasePolicy, TenantPolicy, UserPolicy

__all__ = [
    "__version__",
    "__version_info__",
    "RLSModel",
    "BasePolicy",
    "TenantPolicy",
    "UserPolicy",
]