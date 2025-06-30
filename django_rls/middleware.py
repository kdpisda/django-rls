"""RLS Context Middleware."""

import logging
from typing import Optional, Callable

from django.http import HttpRequest, HttpResponse
from django.db import connection
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class RLSContextMiddleware:
    """Middleware to set RLS context variables."""
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Set RLS context before processing request
        self._set_rls_context(request)
        
        response = self.get_response(request)
        
        # Clear RLS context after processing
        self._clear_rls_context()
        
        return response
    
    def _set_rls_context(self, request: HttpRequest) -> None:
        """Set RLS context variables in PostgreSQL."""
        from .db.functions import set_rls_context
        
        # Set user context
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            set_rls_context('user_id', request.user.id, is_local=True)
        
        # Set tenant context if available
        tenant_id = self._get_tenant_id(request)
        if tenant_id:
            set_rls_context('tenant_id', tenant_id, is_local=True)
    
    def _clear_rls_context(self) -> None:
        """Clear RLS context variables."""
        from .db.functions import set_rls_context
        
        set_rls_context('user_id', '', is_local=True)
        set_rls_context('tenant_id', '', is_local=True)
    
    def _get_tenant_id(self, request: HttpRequest) -> Optional[int]:
        """Extract tenant ID from request."""
        # This can be customized based on your tenant detection logic
        # Example implementations:
        
        # 1. From subdomain
        if hasattr(request, 'tenant'):
            return request.tenant.id
        
        # 2. From user profile
        if (hasattr(request, 'user') and 
            hasattr(request.user, 'profile') and 
            hasattr(request.user.profile, 'tenant_id')):
            return request.user.profile.tenant_id
        
        # 3. From session
        return request.session.get('tenant_id')