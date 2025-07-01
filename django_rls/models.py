"""RLS Model base class."""

import logging
from typing import List, Optional, Type, TYPE_CHECKING

from django.db import models, connection
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .exceptions import PolicyError, ConfigurationError

if TYPE_CHECKING:
    from .policies import BasePolicy

logger = logging.getLogger(__name__)


class RLSModelMeta(models.base.ModelBase):
    """Metaclass for RLS models."""
    
    def __new__(cls, name, bases, namespace, **kwargs):
        # Extract rls_policies from Meta before Django processes it
        meta = namespace.get('Meta')
        rls_policies = []
        if meta:
            rls_policies = getattr(meta, 'rls_policies', [])
            # Remove it so Django doesn't complain
            if hasattr(meta, 'rls_policies'):
                delattr(meta, 'rls_policies')
        
        new_class = super().__new__(cls, name, bases, namespace, **kwargs)
        
        # Process RLS policies
        if rls_policies:
            cls._validate_policies(rls_policies)
            new_class._rls_policies = rls_policies
        else:
            # Check if any parent class has RLS policies
            for base in bases:
                if hasattr(base, '_rls_policies'):
                    new_class._rls_policies = base._rls_policies
                    break
            else:
                new_class._rls_policies = []
            
        return new_class
    
    @staticmethod
    def _validate_policies(policies: List['BasePolicy']) -> None:
        """Validate RLS policies."""
        if not isinstance(policies, list):
            raise ConfigurationError("rls_policies must be a list")
        
        # Import here to avoid circular dependency
        from .policies import BasePolicy
        
        for policy in policies:
            if not isinstance(policy, BasePolicy):
                raise PolicyError(f"Policy {policy} must inherit from BasePolicy")


class RLSModel(models.Model, metaclass=RLSModelMeta):
    """Base model class that provides RLS functionality."""
    
    class Meta:
        abstract = True
    
    @classmethod
    def enable_rls(cls) -> None:
        """Enable RLS for this model's table."""
        from django.db import connections
        
        # Models don't have _state, use default connection
        db_alias = 'default'
        connection = connections[db_alias]
        
        with connection.schema_editor() as schema_editor:
            if hasattr(schema_editor, 'enable_rls'):
                # Enable RLS
                schema_editor.enable_rls(cls)
                
                # Create policies
                for policy in cls._rls_policies:
                    schema_editor.create_policy(cls, policy)
                    
                logger.info(f"RLS enabled for {cls._meta.db_table}")
            else:
                logger.warning(
                    f"Database backend {connection.vendor} does not support RLS. "
                    f"Use 'django_rls.backends.postgresql' as your database ENGINE."
                )
    
    @classmethod
    def disable_rls(cls) -> None:
        """Disable RLS for this model's table."""
        from django.db import connections
        
        # Models don't have _state, use default connection
        db_alias = 'default'
        connection = connections[db_alias]
        
        with connection.schema_editor() as schema_editor:
            if hasattr(schema_editor, 'disable_rls'):
                # Drop policies
                for policy in cls._rls_policies:
                    schema_editor.drop_policy(cls, policy.name)
                
                # Disable RLS
                schema_editor.disable_rls(cls)
                
                logger.info(f"RLS disabled for {cls._meta.db_table}")
            else:
                logger.warning(
                    f"Database backend {connection.vendor} does not support RLS."
                )


@receiver(post_migrate)
def enable_rls_on_migrate(sender, **kwargs):
    """Enable RLS after migrations."""
    # Only process models from the migrated app
    if sender.name == 'django_rls':
        return
        
    from django.apps import apps
    
    for model in apps.get_models():
        if issubclass(model, RLSModel) and hasattr(model, '_rls_policies') and model._rls_policies:
            if model._meta.app_label == sender.name:
                try:
                    model.enable_rls()
                except Exception as e:
                    logger.error(f"Failed to enable RLS for {model._meta.label}: {e}")