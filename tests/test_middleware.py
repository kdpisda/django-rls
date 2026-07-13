"""Tests for RLS middleware."""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import TestCase, override_settings

from django_rls.middleware import RLSContextMiddleware


@pytest.mark.django_db
class TestRLSContextMiddleware(TestCase):
    """Test RLS context middleware."""

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        get_response = Mock()
        middleware = RLSContextMiddleware(get_response)
        assert middleware.get_response == get_response

    @patch("django_rls.middleware.reset_connection_rls_context")
    @patch("django_rls.middleware.apply_rls_context")
    @patch("django_rls.middleware.clear_rls_context")
    def test_set_user_context(self, mock_clear, mock_apply, mock_reset):
        """Test setting user context."""
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)

        request = Mock()
        request.user = Mock(id=123)
        request.session = {}
        del request.tenant

        middleware(request)

        mock_apply.assert_called_once_with(
            {"user_id": 123}, system=True, source="middleware"
        )
        mock_clear.assert_called_once()

    @patch("django_rls.middleware.reset_connection_rls_context")
    @patch("django_rls.middleware.apply_rls_context")
    @patch("django_rls.middleware.clear_rls_context")
    def test_anonymous_user_context(self, mock_clear, mock_apply, mock_reset):
        """Test handling anonymous user."""
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)

        request = Mock()
        del request.tenant
        request.user = AnonymousUser()
        request.session = {}

        middleware(request)

        mock_apply.assert_called_once_with({}, system=True, source="middleware")

    @patch("django_rls.middleware.reset_connection_rls_context")
    @patch("django_rls.middleware.apply_rls_context")
    @patch("django_rls.middleware.clear_rls_context")
    def test_tenant_context_from_request(self, mock_clear, mock_apply, mock_reset):
        """Test setting tenant context from request.tenant."""
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)

        request = Mock()
        request.user = AnonymousUser()
        request.tenant = Mock(id=456)
        request.session = {}

        middleware(request)

        mock_apply.assert_called_once_with(
            {"tenant_id": 456}, system=True, source="middleware"
        )

    @patch("django_rls.middleware.reset_connection_rls_context")
    @patch("django_rls.middleware.apply_rls_context")
    @patch("django_rls.middleware.clear_rls_context")
    def test_tenant_context_from_session_blocked_by_default(
        self, mock_clear, mock_apply, mock_reset
    ):
        """Session tenant_id is ignored unless ALLOW_SESSION_TENANT is enabled."""
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)

        request = Mock()
        request.user = AnonymousUser()
        request.session = {"tenant_id": 789}
        del request.tenant

        middleware(request)

        mock_apply.assert_called_once_with({}, system=True, source="middleware")

    @override_settings(DJANGO_RLS={"ALLOW_SESSION_TENANT": True})
    @patch("django_rls.middleware.reset_connection_rls_context")
    @patch("django_rls.middleware.apply_rls_context")
    @patch("django_rls.middleware.clear_rls_context")
    def test_tenant_context_from_session_when_enabled(
        self, mock_clear, mock_apply, mock_reset
    ):
        """Session tenant_id is used only when explicitly opted in."""
        get_response = Mock(return_value=HttpResponse())
        middleware = RLSContextMiddleware(get_response)

        request = Mock()
        request.user = AnonymousUser()
        request.session = {"tenant_id": 789}
        del request.tenant

        middleware(request)

        mock_apply.assert_called_once_with(
            {"tenant_id": 789}, system=True, source="middleware"
        )
