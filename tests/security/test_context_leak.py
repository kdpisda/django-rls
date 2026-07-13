"""
Security Test: Context Leakage via Connection Pools

Middleware must clear RLS context even when the view raises.
"""

from unittest.mock import Mock

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from django_rls.context import get_active_rls_context
from django_rls.db.functions import get_rls_context
from django_rls.middleware import RLSContextMiddleware


@pytest.mark.security
@pytest.mark.django_db
def test_exception_still_clears_context(require_postgresql):
    factory = RequestFactory()
    request = factory.get("/error")
    request.user = Mock(id=123, spec=[])
    request.session = {}

    seen = {}

    def error_view(_request):
        seen["user_id"] = get_rls_context("user_id")
        raise ValueError("Crash inside view")

    middleware = RLSContextMiddleware(error_view)

    with pytest.raises(ValueError):
        middleware(request)

    assert seen["user_id"] == "123"
    assert get_rls_context("user_id") in (None, "")
    assert get_active_rls_context() == {}


@pytest.mark.security
@pytest.mark.django_db
def test_success_clears_context(require_postgresql):
    factory = RequestFactory()
    request = factory.get("/")
    request.session = {}
    request.user = Mock(id=456, spec=[])

    seen = {}

    def capture_view(_request):
        seen["user_id"] = get_rls_context("user_id")
        return HttpResponse("OK")

    middleware = RLSContextMiddleware(capture_view)
    middleware(request)

    assert seen["user_id"] == "456"
    assert get_rls_context("user_id") in (None, "")
    assert get_active_rls_context() == {}