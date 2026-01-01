"""
Security Test: Context Leakage via Connection Pools

This test simulates connection pooling behavior to prove that
RLS context persists (leaks) when exceptions occur.
Refactored to use mocks since valid Postgres DB is not guaranteed in CI.
"""
import pytest
from unittest.mock import Mock, patch, ANY
from django.test import RequestFactory, SimpleTestCase
from django.http import HttpResponse

from django_rls.middleware import RLSContextMiddleware

class TestContextLeakage(SimpleTestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        
    @patch('django_rls.middleware.RLSContextMiddleware._set_rls_context')
    @patch('django_rls.middleware.RLSContextMiddleware._clear_rls_context')
    def test_exception_leaks_context_logic(self, mock_clear, mock_set):
        """
        Critical Vulnerability Test:
        If a view raises an exception, the middleware MUST still call _clear_rls_context.
        """
        request = self.factory.get('/error')
        request.user = Mock(id=123)
        
        def error_view(request):
            raise ValueError("Crash inside view")
            
        middleware = RLSContextMiddleware(error_view)
        
        try:
            middleware(request)
        except ValueError:
            pass # Expected crash
            
        # Assertion: process_exception logic should ensure cleanup
        
        if not mock_clear.called:
             pytest.fail("Security Failure: Context was NOT cleared after exception!")

        mock_set.assert_called_once()
        mock_clear.assert_called_once()

    @patch('django_rls.middleware.RLSContextMiddleware._set_rls_context')
    @patch('django_rls.middleware.RLSContextMiddleware._clear_rls_context')
    def test_success_clears_context(self, mock_clear, mock_set):
        """Control test: A normal request should clear context."""
        request = self.factory.get('/')
        request.user = Mock(id=456)
        
        def success_view(request):
            return HttpResponse("OK")
            
        middleware = RLSContextMiddleware(success_view)
        middleware(request)
        
        mock_set.assert_called_once()
        mock_clear.assert_called_once()
