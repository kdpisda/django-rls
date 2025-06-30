"""Custom middleware for tenant detection."""

from django.http import HttpRequest


class TenantMiddleware:
    """Middleware to detect and set tenant from subdomain."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        # Extract tenant from subdomain
        host = request.get_host().split(':')[0]  # Remove port if present
        subdomain = host.split('.')[0]
        
        # Load tenant based on subdomain
        if subdomain and subdomain != 'www':
            try:
                from .models import Tenant, TenantMembership
                tenant = Tenant.objects.get(slug=subdomain)
                
                # Check if user is member of this tenant
                if request.user.is_authenticated:
                    membership = TenantMembership.objects.filter(
                        user=request.user,
                        tenant=tenant
                    ).first()
                    
                    if membership:
                        request.tenant = tenant
                        request.session['tenant_id'] = tenant.id
            except Tenant.DoesNotExist:
                pass
        
        response = self.get_response(request)
        return response