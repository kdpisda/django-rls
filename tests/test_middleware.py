"""Tests for RLS middleware."""

import pytest
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse

from django_rls.middleware import RLSContextMiddleware


@pytest.mark.django_db
class TestRLSContextMiddleware(TestCase):
    """Test RLS context middleware."""
    
    def test_middleware_initialization(self):
        """Test middleware initialization."""
        get_response = Mock()
        middleware = RLSContextMiddleware(get_response)
        assert middleware.get_response == get_response
    
    @patch('django_rls.db.functions.set_rls_context')
    def test_set_user_context(self, mock_set_rls_context):
        """Test setting user context."""
        # Setup
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)
        
        # Create mock request with user
        request = Mock()
        request.user = Mock(id=123)
        request.session = {}
        
        # Call middleware
        middleware(request)
        
        # Verify set_rls_context was called for user
        mock_set_rls_context.assert_any_call('user_id', 123, is_local=False)
    
    @patch('django_rls.db.functions.set_rls_context')
    def test_anonymous_user_context(self, mock_set_rls_context):
        """Test handling anonymous user."""
        # Setup
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)
        
        # Create mock request with anonymous user
        request = Mock()
        request.user = AnonymousUser()
        request.session = {}
        
        # Call middleware
        middleware(request)
        
        # Verify set_rls_context was called with empty values for clearing
        # Should be called twice during _clear_rls_context
        assert mock_set_rls_context.call_count >= 2
        
        # Check that user_id was cleared
        mock_set_rls_context.assert_any_call('user_id', '', is_local=False)
        # Check that tenant_id was cleared
        mock_set_rls_context.assert_any_call('tenant_id', '', is_local=False)
    
    @patch('django_rls.db.functions.set_rls_context')
    def test_tenant_context_from_request(self, mock_set_rls_context):
        """Test setting tenant context from request.tenant."""
        # Setup
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)
        
        # Create mock request with tenant
        request = Mock()
        request.user = AnonymousUser()
        request.tenant = Mock(id=456)
        request.session = {}
        
        # Call middleware
        middleware(request)
        
        # Verify set_rls_context was called for tenant
        mock_set_rls_context.assert_any_call('tenant_id', 456, is_local=False)
    
    @patch('django_rls.db.functions.set_rls_context')
    def test_tenant_context_from_session(self, mock_set_rls_context):
        """Test setting tenant context from session."""
        # Setup
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)
        
        # Create mock request with tenant in session
        request = Mock()
        request.user = AnonymousUser()
        request.session = {'tenant_id': 789}
        
        # Mock that request doesn't have tenant attribute
        del request.tenant
        
        # Call middleware
        middleware(request)
        
        # Verify set_rls_context was called for tenant
        mock_set_rls_context.assert_any_call('tenant_id', 789, is_local=False)