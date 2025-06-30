"""Tenant-based usage example."""

from django.db import models
from django.contrib.auth.models import User

from django_rls.models import RLSModel
from django_rls.policies import TenantPolicy, UserPolicy


class Tenant(models.Model):
    """Tenant/Organization model."""
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class TenantMembership(models.Model):
    """User membership in tenant."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='member')
    
    class Meta:
        unique_together = ('user', 'tenant')


class TenantProject(RLSModel):
    """Project that belongs to a tenant."""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        rls_policies = [
            TenantPolicy('tenant_project_policy', tenant_field='tenant'),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class ProjectTask(RLSModel):
    """Task within a project."""
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    project = models.ForeignKey(TenantProject, on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='todo')
    
    class Meta:
        rls_policies = [
            # Inherit tenant from project
            TenantPolicy('task_tenant_policy', tenant_field='project__tenant'),
            # Users can only see tasks assigned to them or created by them
            UserPolicy('task_user_policy', user_field='assigned_to'),
        ]