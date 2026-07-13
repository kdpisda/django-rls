"""
Security Test: Context Leakage via Connection Pools

Middleware must clear RLS context even when the view raises.
"""

from unittest.mock import Mock, patch

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from django_rls.middleware import RLSContextMiddleware


@pytest.mark.security
@patch("django_rls.middleware.reset_connection_rls_context")
@patch("django_rls.middleware.apply_rls_context")
@patch("django_rls.middleware.clear_rls_context")
def test_exception_still_clears_context(mock_clear, mock_apply, mock_reset):
    factory = RequestFactory()
    request = factory.get("/error")
    request.user = Mock(id=123, spec=[])
    request.session = {}

    def error_view(_request):
        raise ValueError("Crash inside view")

    middleware = RLSContextMiddleware(error_view)

    with pytest.raises(ValueError):
        middleware(request)

    mock_apply.assert_called_once()
    mock_clear.assert_called_once()


@pytest.mark.security
@patch("django_rls.middleware.reset_connection_rls_context")
@patch("django_rls.middleware.apply_rls_context")
@patch("django_rls.middleware.clear_rls_context")
def test_success_clears_context(mock_clear, mock_apply, mock_reset):
    factory = RequestFactory()
    request = factory.get("/")
    request.user = Mock(id=456, spec=[])
    request.session = {}

    middleware = RLSContextMiddleware(lambda _r: HttpResponse("OK"))
    middleware(request)

    mock_apply.assert_called_once()
    mock_clear.assert_called_once()
