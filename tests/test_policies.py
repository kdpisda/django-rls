"""Tests for RLS policies."""

import pytest
from django_rls.policies import TenantPolicy, UserPolicy, CustomPolicy
from django_rls.exceptions import PolicyError


class TestTenantPolicy:
    """Test tenant-based policies."""
    
    def test_tenant_policy_creation(self):
        """Test creating a tenant policy."""
        policy = TenantPolicy('test_policy', tenant_field='organization')
        assert policy.name == 'test_policy'
        assert policy.tenant_field == 'organization'
    
    def test_tenant_policy_sql_expression(self):
        """Test SQL expression generation."""
        policy = TenantPolicy('test_policy', tenant_field='tenant')
        expected = "tenant_id = current_setting('rls.tenant_id')::integer"
        assert policy.get_sql_expression() == expected
    
    def test_tenant_policy_missing_field(self):
        """Test error when tenant_field is missing."""
        with pytest.raises(PolicyError):
            TenantPolicy('test_policy', tenant_field='')


class TestUserPolicy:
    """Test user-based policies."""
    
    def test_user_policy_creation(self):
        """Test creating a user policy."""
        policy = UserPolicy('test_policy')
        assert policy.name == 'test_policy'
        assert policy.user_field == 'user'
    
    def test_user_policy_sql_expression(self):
        """Test SQL expression generation."""
        policy = UserPolicy('test_policy', user_field='owner')
        expected = "owner_id = current_setting('rls.user_id')::integer"
        assert policy.get_sql_expression() == expected


class TestCustomPolicy:
    """Test custom policies."""
    
    def test_custom_policy_creation(self):
        """Test creating a custom policy."""
        expression = "created_at > current_date - interval '30 days'"
        policy = CustomPolicy('test_policy', expression=expression)
        assert policy.get_sql_expression() == expression
    
    def test_custom_policy_missing_expression(self):
        """Test error when expression is missing."""
        with pytest.raises(PolicyError):
            CustomPolicy('test_policy', expression='')