"""Tests for RLS middleware."""

from unittest.mock import Mock

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from django_rls.context import get_active_rls_context
from django_rls.db.functions import get_rls_context
from django_rls.middleware import RLSContextMiddleware


@pytest.mark.django_db
class TestRLSContextMiddleware(TestCase):
    """Test RLS context middleware against a live PostgreSQL connection."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_middleware_initialization(self):
        get_response = Mock()
        middleware = RLSContextMiddleware(get_response)
        assert middleware.get_response == get_response

    def test_set_user_context(self):
        seen = {}

        def capture_view(_request):
            seen["user_id"] = get_rls_context("user_id")
            return HttpResponse()

        middleware = RLSContextMiddleware(capture_view)
        request = self.factory.get("/")
        request.user = Mock(id=123, spec=[])
        request.session = {}

        middleware(request)

        assert seen["user_id"] == "123"
        assert get_rls_context("user_id") in (None, "")
        assert get_active_rls_context() == {}

    def test_anonymous_user_context(self):
        seen = {}

        def capture_view(_request):
            seen["user_id"] = get_rls_context("user_id")
            return HttpResponse()

        middleware = RLSContextMiddleware(capture_view)
        request = self.factory.get("/")
        request.user = AnonymousUser()
        request.session = {}

        middleware(request)

        assert seen["user_id"] in (None, "")
        assert get_rls_context("user_id") in (None, "")

    def test_tenant_context_from_request(self):
        seen = {}

        def capture_view(_request):
            seen["tenant_id"] = get_rls_context("tenant_id")
            return HttpResponse()

        middleware = RLSContextMiddleware(capture_view)
        request = self.factory.get("/")
        request.user = AnonymousUser()
        request.tenant = Mock(id=456)
        request.session = {}

        middleware(request)

        assert seen["tenant_id"] == "456"

    def test_tenant_context_from_session_blocked_by_default(self):
        seen = {}

        def capture_view(_request):
            seen["tenant_id"] = get_rls_context("tenant_id")
            return HttpResponse()

        middleware = RLSContextMiddleware(capture_view)
        request = self.factory.get("/")
        request.user = AnonymousUser()
        request.session = {"tenant_id": 789}

        middleware(request)

        assert seen["tenant_id"] in (None, "")

    @override_settings(DJANGO_RLS={"ALLOW_SESSION_TENANT": True})
    def test_tenant_context_from_session_when_enabled(self):
        seen = {}

        def capture_view(_request):
            seen["tenant_id"] = get_rls_context("tenant_id")
            return HttpResponse()

        middleware = RLSContextMiddleware(capture_view)
        request = self.factory.get("/")
        request.user = AnonymousUser()
        request.session = {"tenant_id": 789}

        middleware(request)

        assert seen["tenant_id"] == "789"