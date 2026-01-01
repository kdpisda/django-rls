"""RLS Context Middleware."""

import logging
from typing import Callable, Optional

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.utils.module_loading import import_string

from .db.functions import set_rls_context

logger = logging.getLogger(__name__)


class RLSContextMiddleware:
    """Middleware to set RLS context variables."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Set RLS context before processing request
        self._set_rls_context(request)

        try:
            response = self.get_response(request)
        finally:
            # Clear RLS context after processing, even if exception occurs
            self._clear_rls_context(request)

        return response

    def _set_rls_context(self, request: HttpRequest) -> None:
        """Set RLS context variables in PostgreSQL."""

        request.rls_set_keys = []

        def set_and_track(key, value):
            set_rls_context(key, value, is_local=False)
            request.rls_set_keys.append(key)

        # Set user context
        if hasattr(request, "user") and not isinstance(request.user, AnonymousUser):
            set_and_track("user_id", request.user.id)

        # Set tenant context if available
        tenant_id = self._get_tenant_id(request)
        if tenant_id:
            set_and_track("tenant_id", tenant_id)

        # Run Custom Context Processors

        processors = getattr(settings, "RLS_CONTEXT_PROCESSORS", [])
        for proc_path in processors:
            try:
                processor = import_string(proc_path)
                context_data = processor(request)
                if isinstance(context_data, dict):
                    for key, value in context_data.items():
                        set_and_track(key, value)
            except Exception as e:
                logger.error(f"Failed to run RLS context processor {proc_path}: {e}")

    def _clear_rls_context(self, request: HttpRequest = None) -> None:
        """Clear RLS context variables."""

        if request and hasattr(request, "rls_set_keys"):
            for key in request.rls_set_keys:
                set_rls_context(key, "", is_local=False)
        else:
            # Fallback for safety or if request not provided
            # (though middleware flow usually provides it)
            set_rls_context("user_id", "", is_local=False)
            set_rls_context("tenant_id", "", is_local=False)

    def _get_tenant_id(self, request: HttpRequest) -> Optional[int]:
        """Extract tenant ID from request."""
        # This can be customized based on your tenant detection logic
        # Example implementations:

        # 1. From subdomain
        if hasattr(request, "tenant"):
            return request.tenant.id

        # 2. From user profile
        if (
            hasattr(request, "user")
            and hasattr(request.user, "profile")
            and hasattr(request.user.profile, "tenant_id")
        ):
            return request.user.profile.tenant_id

        # 3. From session
        return request.session.get("tenant_id")
