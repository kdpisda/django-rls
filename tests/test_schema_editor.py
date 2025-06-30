"""Tests for RLS schema editor."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from django.db import connection
from django.test import TestCase

from django_rls.backends.postgresql.base import RLSDatabaseSchemaEditor
from django_rls.policies import TenantPolicy, UserPolicy, CustomPolicy


class TestRLSDatabaseSchemaEditor(TestCase):
    """Test RLS database schema editor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.connection = Mock()
        self.editor = RLSDatabaseSchemaEditor(self.connection)
        self.editor.execute = Mock()
        # Override quote_name to return quoted strings
        self.editor.quote_name = lambda x: f'"{x}"'
    
    def test_enable_rls(self):
        """Test enabling RLS on a table."""
        model = Mock()
        model._meta.db_table = 'test_table'
        
        self.editor.enable_rls(model)
        
        # Check the SQL was executed
        self.editor.execute.assert_called_once()
        call_args = self.editor.execute.call_args[0][0]
        assert call_args == 'ALTER TABLE "test_table" ENABLE ROW LEVEL SECURITY'
    
    def test_disable_rls(self):
        """Test disabling RLS on a table."""
        model = Mock()
        model._meta.db_table = 'test_table'
        
        self.editor.disable_rls(model)
        
        self.editor.execute.assert_called_once()
        call_args = self.editor.execute.call_args[0][0]
        assert call_args == 'ALTER TABLE "test_table" DISABLE ROW LEVEL SECURITY'
    
    def test_force_rls(self):
        """Test forcing RLS on a table."""
        model = Mock()
        model._meta.db_table = 'test_table'
        
        self.editor.force_rls(model)
        
        self.editor.execute.assert_called_once()
        call_args = self.editor.execute.call_args[0][0]
        assert call_args == 'ALTER TABLE "test_table" FORCE ROW LEVEL SECURITY'
    
    def test_create_user_policy(self):
        """Test creating a user-based policy."""
        model = Mock()
        model._meta.db_table = 'test_table'
        
        policy = UserPolicy('test_policy', user_field='owner')
        
        self.editor.create_policy(model, policy)
        
        # Check that execute was called with proper SQL
        call_args = self.editor.execute.call_args[0][0]
        assert 'CREATE POLICY "test_policy"' in call_args
        assert 'ON "test_table"' in call_args
        assert 'AS PERMISSIVE' in call_args
        assert 'FOR ALL' in call_args
        assert 'TO public' in call_args
        assert 'USING (owner_id = current_setting(\'rls.user_id\')::integer)' in call_args
    
    def test_create_tenant_policy(self):
        """Test creating a tenant-based policy."""
        model = Mock()
        model._meta.db_table = 'test_table'
        
        policy = TenantPolicy('test_policy', tenant_field='organization')
        
        self.editor.create_policy(model, policy)
        
        call_args = self.editor.execute.call_args[0][0]
        assert 'USING (organization_id = current_setting(\'rls.tenant_id\')::integer)' in call_args
    
    def test_create_custom_policy(self):
        """Test creating a custom policy."""
        model = Mock()
        model._meta.db_table = 'test_table'
        
        policy = CustomPolicy('test_policy', expression='is_public = true')
        
        self.editor.create_policy(model, policy)
        
        call_args = self.editor.execute.call_args[0][0]
        assert 'USING (is_public = true)' in call_args
    
    def test_create_policy_with_operation(self):
        """Test creating a policy with specific operation."""
        model = Mock()
        model._meta.db_table = 'test_table'
        
        policy = UserPolicy(
            'test_policy', 
            user_field='owner',
            operation='SELECT',
            permissive=False
        )
        
        self.editor.create_policy(model, policy)
        
        call_args = self.editor.execute.call_args[0][0]
        assert 'AS RESTRICTIVE' in call_args
        assert 'FOR SELECT' in call_args
    
    def test_drop_policy(self):
        """Test dropping a policy."""
        model = Mock()
        model._meta.db_table = 'test_table'
        
        self.editor.drop_policy(model, 'test_policy')
        
        self.editor.execute.assert_called_once()
        call_args = self.editor.execute.call_args[0][0]
        assert call_args == 'DROP POLICY IF EXISTS "test_policy" ON "test_table"'
    
    def test_alter_policy(self):
        """Test altering a policy."""
        model = Mock()
        model._meta.db_table = 'test_table'
        
        policy = Mock()
        policy.name = 'test_policy'
        policy.get_using_expression = Mock(return_value='new_expression')
        policy.get_check_expression = Mock(return_value=None)
        
        self.editor.alter_policy(model, policy)
        
        call_args = self.editor.execute.call_args[0][0]
        # The SQL is formatted with template variables
        assert 'ALTER POLICY' in call_args
        assert 'test_policy' in call_args
        assert 'test_table' in call_args
        assert 'USING (new_expression)' in call_args


class TestDatabaseWrapper(TestCase):
    """Test custom database wrapper."""
    
    @patch('django_rls.backends.postgresql.base.DatabaseWrapper')
    def test_schema_editor_class(self, mock_base):
        """Test that our wrapper uses the custom schema editor."""
        from django_rls.backends.postgresql.base import DatabaseWrapper
        
        wrapper = DatabaseWrapper({})
        assert wrapper.SchemaEditorClass == RLSDatabaseSchemaEditor
    
    @patch('django_rls.backends.postgresql.base.DatabaseWrapper')
    def test_schema_editor_method(self, mock_base):
        """Test schema_editor method returns our custom editor."""
        from django_rls.backends.postgresql.base import DatabaseWrapper
        
        wrapper = DatabaseWrapper({})
        editor = wrapper.schema_editor()
        
        assert isinstance(editor, RLSDatabaseSchemaEditor)