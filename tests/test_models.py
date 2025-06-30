"""
Tests for RLS models.

Following Django REST Framework's testing patterns.
"""
import pytest
from django.test import TestCase
from django.db import models

from django_rls.models import RLSModel
from django_rls.policies import TenantPolicy, UserPolicy
from django_rls.exceptions import PolicyError, ConfigurationError


class TestRLSModelCreation(TestCase):
    """Test RLS model creation and metaclass behavior."""
    
    def test_create_rls_model_with_policies(self):
        """Test creating an RLS model with policies."""
        # This happens at import time in tests/models.py
        from tests.models import UserOwnedModel
        
        assert hasattr(UserOwnedModel, '_rls_policies')
        assert len(UserOwnedModel._rls_policies) == 1
        assert isinstance(UserOwnedModel._rls_policies[0], UserPolicy)
    
    def test_create_rls_model_without_policies(self):
        """Test creating an RLS model without policies."""
        class TestModel(RLSModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'tests'
        
        assert hasattr(TestModel, '_rls_policies')
        assert TestModel._rls_policies == []
    
    def test_inherit_rls_policies(self):
        """Test that RLS policies are inherited from parent."""
        from tests.models import UserOwnedModel
        
        class ChildModel(UserOwnedModel):
            extra_field = models.CharField(max_length=50)
            
            class Meta:
                app_label = 'tests'
        
        # Should inherit parent's policies
        assert len(ChildModel._rls_policies) == len(UserOwnedModel._rls_policies)
    
    def test_invalid_policy_configuration(self):
        """Test that invalid policies raise errors."""
        with self.assertRaises(ConfigurationError) as cm:
            # This should fail during metaclass processing
            class BadModel(RLSModel):
                name = models.CharField(max_length=100)
                
                class Meta:
                    app_label = 'tests'
                    # Invalid - should be a list of policy instances
                    rls_policies = "not_a_list"
        
        assert "rls_policies must be a list" in str(cm.exception)


class TestRLSModelMethods(TestCase):
    """Test RLS model methods."""
    
    @pytest.mark.postgresql
    def test_enable_rls(self):
        """Test enabling RLS on a model."""
        from tests.models import UserOwnedModel
        from django.db import connection
        
        # This would actually enable RLS in PostgreSQL
        # For now, just test that the method exists
        assert hasattr(UserOwnedModel, 'enable_rls')
        assert callable(UserOwnedModel.enable_rls)
    
    @pytest.mark.postgresql  
    def test_disable_rls(self):
        """Test disabling RLS on a model."""
        from tests.models import UserOwnedModel
        
        # This would actually disable RLS in PostgreSQL
        # For now, just test that the method exists
        assert hasattr(UserOwnedModel, 'disable_rls')
        assert callable(UserOwnedModel.disable_rls)


class TestPolicyExtraction(TestCase):
    """Test policy extraction from Meta class."""
    
    def test_multiple_policies(self):
        """Test model with multiple policies."""
        from tests.models import ComplexModel
        
        assert len(ComplexModel._rls_policies) == 3
        policy_types = [type(p).__name__ for p in ComplexModel._rls_policies]
        assert 'UserPolicy' in policy_types
        assert 'TenantPolicy' in policy_types
        assert 'CustomPolicy' in policy_types
    
    def test_policy_names_unique(self):
        """Test that policy names are preserved."""
        from tests.models import ComplexModel
        
        policy_names = [p.name for p in ComplexModel._rls_policies]
        assert 'owner_policy' in policy_names
        assert 'org_policy' in policy_names
        assert 'public_policy' in policy_names