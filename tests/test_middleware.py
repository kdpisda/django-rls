"""Tests for RLS middleware."""

import pytest
from unittest.mock import Mock, patch
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse

from django_rls.middleware import RLSContextMiddleware


class TestRLSContextMiddleware:
    """Test RLS context middleware."""
    
    def test_middleware_initialization(self):
        """Test middleware initialization."""
        get_response = Mock()
        middleware = RLSContextMiddleware(get_response)
        assert middleware.get_response == get_response
    
    @patch('django_rls.middleware.connection')
    def test_set_user_context(self, mock_connection):
        """Test setting user context."""
        # Setup
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)
        
        # Create mock request with user
        request = Mock()
        request.user = Mock(id=123)
        
        # Create mock cursor
        mock_cursor = Mock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Call middleware
        middleware(request)
        
        # Verify set_config was called for user
        mock_cursor.execute.assert_any_call(
            "SELECT set_config('rls.user_id', %s, true)", ['123']
        )
    
    @patch('django_rls.middleware.connection')
    def test_anonymous_user_context(self, mock_connection):
        """Test handling anonymous user."""
        # Setup
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)
        
        # Create mock request with anonymous user
        request = Mock()
        request.user = AnonymousUser()
        request.session = {}
        
        # Create mock cursor
        mock_cursor = Mock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Call middleware
        middleware(request)
        
        # Verify set_config was not called for user_id
        calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
        assert not any("rls.user_id" in call and call != "SELECT set_config('rls.user_id', '', true)" for call in calls)