"""Tests for RLS models."""

import pytest
from django.test import TestCase, TransactionTestCase
from django.db import connection, models
from django.contrib.auth.models import User

from django_rls.models import RLSModel
from django_rls.policies import TenantPolicy, UserPolicy
from django_rls.exceptions import PolicyError, ConfigurationError


class TestRLSModel(TransactionTestCase):
    """Test RLS model functionality."""
    
    def test_rls_model_creation(self):
        """Test creating an RLS model."""
        class TestModel(RLSModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'test'
                rls_policies = [
                    UserPolicy('user_policy'),
                ]
        
        self.assertEqual(len(TestModel._rls_policies), 1)
        self.assertIsInstance(TestModel._rls_policies[0], UserPolicy)
    
    def test_invalid_policy_configuration(self):
        """Test invalid policy configuration raises error."""
        with self.assertRaises(ConfigurationError):
            class TestModel(RLSModel):
                name = models.CharField(max_length=100)
                
                class Meta:
                    app_label = 'test'
                    rls_policies = "invalid_policy"  # Should be list
    
    def test_enable_disable_rls(self):
        """Test enabling and disabling RLS."""
        # This would require actual database interaction
        # Implementation depends on test database setup
        pass