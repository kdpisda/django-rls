"""
Tests for RLS policies.

Following Django REST Framework's testing patterns.
"""
import pytest
from django.test import TestCase

from django_rls.policies import TenantPolicy, UserPolicy, CustomPolicy, BasePolicy
from django_rls.exceptions import PolicyError


class TestBasePolicy(TestCase):
    """Test base policy functionality."""
    
    def test_policy_requires_name(self):
        """Test that policies require a name."""
        with pytest.raises(PolicyError) as exc_info:
            UserPolicy('', user_field='owner')
        
        assert 'name is required' in str(exc_info.value)
    
    def test_policy_operations(self):
        """Test policy operation types."""
        policy = UserPolicy('test', operation=BasePolicy.SELECT)
        assert policy.operation == BasePolicy.SELECT
        
        policy = UserPolicy('test', operation=BasePolicy.ALL)
        assert policy.operation == BasePolicy.ALL
    
    def test_invalid_operation(self):
        """Test that invalid operations raise error."""
        with pytest.raises(PolicyError) as exc_info:
            UserPolicy('test', operation='INVALID')
        
        assert 'Invalid operation' in str(exc_info.value)
    
    def test_permissive_vs_restrictive(self):
        """Test permissive vs restrictive policies."""
        permissive = UserPolicy('test', permissive=True)
        assert permissive.permissive is True
        
        restrictive = UserPolicy('test', permissive=False)
        assert restrictive.permissive is False


class TestTenantPolicy(TestCase):
    """Test tenant-based policies."""
    
    def test_create_tenant_policy(self):
        """Test creating a tenant policy."""
        policy = TenantPolicy('test_policy', tenant_field='organization')
        
        assert policy.name == 'test_policy'
        assert policy.tenant_field == 'organization'
        assert policy.permissive is True  # Default
    
    def test_tenant_policy_sql_expression(self):
        """Test SQL expression generation for tenant policy."""
        policy = TenantPolicy('test_policy', tenant_field='company')
        
        sql = policy.get_sql_expression()
        assert sql == "company_id = current_setting('rls.tenant_id')::integer"
    
    def test_tenant_policy_requires_field(self):
        """Test that tenant_field is required."""
        with pytest.raises(PolicyError) as exc_info:
            TenantPolicy('test_policy', tenant_field='')
        
        assert 'tenant_field is required' in str(exc_info.value)
    
    def test_tenant_policy_with_custom_operation(self):
        """Test tenant policy with specific operation."""
        policy = TenantPolicy(
            'read_only_policy',
            tenant_field='org',
            operation=BasePolicy.SELECT
        )
        
        assert policy.operation == BasePolicy.SELECT


class TestUserPolicy(TestCase):
    """Test user-based policies."""
    
    def test_create_user_policy(self):
        """Test creating a user policy."""
        policy = UserPolicy('test_policy')
        
        assert policy.name == 'test_policy'
        assert policy.user_field == 'user'  # Default
    
    def test_user_policy_custom_field(self):
        """Test user policy with custom field."""
        policy = UserPolicy('test_policy', user_field='owner')
        
        assert policy.user_field == 'owner'
        sql = policy.get_sql_expression()
        assert sql == "owner_id = current_setting('rls.user_id')::integer"
    
    def test_user_policy_expressions(self):
        """Test USING vs WITH CHECK expressions."""
        policy = UserPolicy('test', operation=BasePolicy.ALL)
        
        # For ALL operations, both should return the same
        using_expr = policy.get_using_expression()
        check_expr = policy.get_check_expression()
        
        assert using_expr == check_expr
        assert 'user_id' in using_expr


class TestCustomPolicy(TestCase):
    """Test custom SQL policies."""
    
    def test_create_custom_policy(self):
        """Test creating a custom policy."""
        expression = "created_at > CURRENT_DATE - INTERVAL '30 days'"
        policy = CustomPolicy('recent_only', expression=expression)
        
        assert policy.name == 'recent_only'
        assert policy.get_sql_expression() == expression
    
    def test_custom_policy_requires_expression(self):
        """Test that expression is required."""
        with pytest.raises(PolicyError) as exc_info:
            CustomPolicy('test_policy', expression='')
        
        assert 'expression is required' in str(exc_info.value)
    
    def test_complex_custom_expression(self):
        """Test complex custom expressions."""
        expression = """
        (user_id = current_setting('rls.user_id')::integer
         OR is_public = true)
        AND NOT is_deleted
        """
        
        policy = CustomPolicy('complex_policy', expression=expression.strip())
        assert 'is_public = true' in policy.get_sql_expression()
        assert 'NOT is_deleted' in policy.get_sql_expression()
    
    def test_custom_policy_with_operations(self):
        """Test custom policy with different operations."""
        policy = CustomPolicy(
            'insert_check',
            expression='department_id = 5',
            operation=BasePolicy.INSERT
        )
        
        assert policy.operation == BasePolicy.INSERT
        # INSERT should have WITH CHECK
        assert policy.get_check_expression() == 'department_id = 5'