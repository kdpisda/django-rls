"""Tests for RLS middleware."""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import TestCase

from django_rls.middleware import RLSContextMiddleware


@pytest.mark.django_db
class TestRLSContextMiddleware(TestCase):
    """Test RLS context middleware."""

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        get_response = Mock()
        middleware = RLSContextMiddleware(get_response)
        assert middleware.get_response == get_response

    @patch("django_rls.middleware.set_rls_context")
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
        mock_set_rls_context.assert_any_call("user_id", 123, is_local=False)

    @patch("django_rls.middleware.set_rls_context")
    def test_anonymous_user_context(self, mock_set_rls_context):
        """Test handling anonymous user."""
        # Setup
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)

        # Create mock request with anonymous user
        request = Mock()
        del request.tenant
        request.user = AnonymousUser()
        request.session = {}

        # Call middleware
        middleware(request)

        # Verify set_rls_context was NOT called for user_id (optimization)
        calls = [c for c in mock_set_rls_context.mock_calls if "user_id" in str(c)]
        assert len(calls) == 0, "Should not set/clear user_id for AnonymousUser"

    @patch("django_rls.middleware.set_rls_context")
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
        mock_set_rls_context.assert_any_call("tenant_id", 456, is_local=False)

    @patch("django_rls.middleware.set_rls_context")
    def test_tenant_context_from_session(self, mock_set_rls_context):
        """Test setting tenant context from session."""
        # Setup
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)

        # Create mock request with tenant in session
        request = Mock()
        request.user = AnonymousUser()
        request.session = {"tenant_id": 789}

        # Mock that request doesn't have tenant attribute
        del request.tenant

        # Call middleware
        middleware(request)

        # Verify set_rls_context was called for tenant
        mock_set_rls_context.assert_any_call("tenant_id", 789, is_local=False)
