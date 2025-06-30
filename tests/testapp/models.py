"""Test models for RLS testing."""

from django.db import models
from django.contrib.auth.models import User

from django_rls.models import RLSModel
from django_rls.policies import TenantPolicy, UserPolicy, CustomPolicy


class Tenant(models.Model):
    """Test tenant model."""
    name = models.CharField(max_length=100)
    
    class Meta:
        app_label = 'testapp'


class UserDocument(RLSModel):
    """Test model with user-based RLS."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'testapp'
        rls_policies = [
            UserPolicy('user_document_policy', user_field='user'),
        ]


class TenantDocument(RLSModel):
    """Test model with tenant-based RLS."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'testapp'
        rls_policies = [
            TenantPolicy('tenant_document_policy', tenant_field='tenant'),
        ]


class ComplexDocument(RLSModel):
    """Test model with multiple policies."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'testapp'
        rls_policies = [
            TenantPolicy('complex_tenant_policy', tenant_field='tenant'),
            UserPolicy('complex_user_policy', user_field='user'),
            CustomPolicy('complex_published_policy', expression='is_published = true'),
        ]