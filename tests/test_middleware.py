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
        """Test handling anonymous user.

        An anonymous user must never have a real user_id *set*, but user_id must
        still be *cleared* (scrubbed) — otherwise stale context left on a reused
        connection by a previous authenticated request would leak into this one.
        """
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

        # No real user_id was ever set (only the empty-string clear is allowed).
        set_user_id_calls = [
            c
            for c in mock_set_rls_context.call_args_list
            if c.args and c.args[0] == "user_id" and c.args[1] != ""
        ]
        assert not set_user_id_calls, "Should not set a real user_id for AnonymousUser"

        # user_id WAS scrubbed to '' so no stale value can leak through.
        cleared_user_id_calls = [
            c
            for c in mock_set_rls_context.call_args_list
            if c.args and c.args[0] == "user_id" and c.args[1] == ""
        ]
        assert cleared_user_id_calls, "Anonymous request must scrub rls.user_id"

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
