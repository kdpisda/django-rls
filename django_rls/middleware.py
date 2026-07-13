"""RLS Context Middleware."""

import logging
from typing import Any, Callable, Dict, Optional

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.utils.module_loading import import_string

from django_rls.conf import rls_config
from django_rls.context import (
    apply_rls_context,
    clear_rls_context,
    reset_connection_rls_context,
)
from django_rls.exceptions import TenantAccessDeniedError

logger = logging.getLogger(__name__)


class RLSContextMiddleware:
    """Middleware to set RLS context variables from the authenticated request."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        reset_connection_rls_context()
        self._set_rls_context(request)

        try:
            response = self.get_response(request)
        finally:
            self._clear_rls_context(request)

        return response

    def _set_rls_context(self, request: HttpRequest) -> None:
        """Set RLS context variables in PostgreSQL."""
        request.rls_set_keys = []
        context_values: Dict[str, Any] = {}

        if hasattr(request, "user") and not isinstance(request.user, AnonymousUser):
            context_values["user_id"] = request.user.id

        tenant_id = self._get_tenant_id(request)
        if tenant_id is not None:
            if not self._validate_tenant_membership(request, tenant_id):
                raise TenantAccessDeniedError(
                    f"User is not authorized for tenant_id={tenant_id!r}."
                )
            context_values["tenant_id"] = tenant_id

        processors = getattr(settings, "RLS_CONTEXT_PROCESSORS", [])
        for proc_path in processors:
            try:
                processor = import_string(proc_path)
                context_data = processor(request)
                if isinstance(context_data, dict):
                    for key, value in context_data.items():
                        if value is not None and value != "":
                            context_values[key] = value
            except Exception as e:
                logger.error("Failed to run RLS context processor %s: %s", proc_path, e)

        apply_rls_context(context_values, system=True, source="middleware")
        request.rls_set_keys = list(context_values.keys())

    def _clear_rls_context(self, request: HttpRequest = None) -> None:
        """Clear RLS context variables."""
        if request and hasattr(request, "rls_set_keys"):
            clear_rls_context(set(request.rls_set_keys))
        else:
            clear_rls_context()

    def _validate_tenant_membership(self, request: HttpRequest, tenant_id: Any) -> bool:
        validator_path = rls_config.tenant_membership_validator
        if not validator_path:
            return True
        validator = import_string(validator_path)
        return bool(validator(request, tenant_id))

    def _get_tenant_id(self, request: HttpRequest) -> Optional[Any]:
        """Extract tenant ID from trusted request attributes only."""
        if hasattr(request, "tenant"):
            return request.tenant.id

        if (
            hasattr(request, "user")
            and not isinstance(request.user, AnonymousUser)
            and hasattr(request.user, "profile")
            and hasattr(request.user.profile, "tenant_id")
        ):
            return request.user.profile.tenant_id

        if rls_config.allow_session_tenant:
            return request.session.get("tenant_id")

        return None
