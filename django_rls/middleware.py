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

    # Context keys the middleware always resets on the way out. Because context
    # is session-scoped (set_config(..., false)) it lives on the physical
    # connection, which Django reuses across requests (CONN_MAX_AGE) and which a
    # pooler (PgBouncer) may hand to another client. These keys are therefore
    # scrubbed unconditionally so a request can never observe context left
    # behind by a previous request on the same connection.
    BASE_CONTEXT_KEYS = ("user_id", "tenant_id")

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Setting context is inside the try so that a failure midway through
        # (e.g. the tenant lookup raising after user_id was already written)
        # still triggers the clear in ``finally`` — otherwise the partially-set,
        # session-scoped context would leak to the next request on this
        # connection.
        try:
            self._set_rls_context(request)
            response = self.get_response(request)
        finally:
            # Clear RLS context after processing, even if an exception occurs
            # while setting context or handling the request.
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
        """Clear RLS context variables.

        Always resets the base keys (``user_id``/``tenant_id``) plus any keys
        this request set via context processors. The base keys are reset even
        when this request set nothing of its own — an anonymous request may land
        on a connection where a previous request left context behind, and must
        scrub it before running any query.
        """
        keys = set(self.BASE_CONTEXT_KEYS)
        if request is not None and hasattr(request, "rls_set_keys"):
            keys.update(request.rls_set_keys)

        for key in keys:
            # Best-effort: one key failing to clear (e.g. a dead connection)
            # must not stop the others, nor mask an in-flight exception that is
            # unwinding through the ``finally`` that called us.
            try:
                set_rls_context(key, "", is_local=False)
            except Exception as e:  # noqa: BLE001 - logged, never swallowed silently
                logger.error(f"Failed to clear RLS context key {key!r}: {e}")

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
