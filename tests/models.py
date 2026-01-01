"""
Test models for Django RLS.

These models are only used in tests.
"""
from django.db import models
from django.contrib.auth.models import User

from django_rls.models import RLSModel
from django_rls.policies import TenantPolicy, UserPolicy, CustomPolicy


class Organization(models.Model):
    """Test organization model."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    
    class Meta:
        app_label = 'tests'


class SimpleModel(models.Model):
    """Simple model without RLS."""
    name = models.CharField(max_length=100)
    
    class Meta:
        app_label = 'tests'


class UserOwnedModel(RLSModel):
    """Model with user-based RLS."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'tests'
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner'),
        ]


class TenantModel(RLSModel):
    """Model with tenant-based RLS."""
    name = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'tests'
        rls_policies = [
            TenantPolicy('org_policy', tenant_field='organization'),
        ]


class ComplexModel(RLSModel):
    """Model with multiple RLS policies."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'tests'
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner'),
            TenantPolicy('org_policy', tenant_field='organization'),
            CustomPolicy('public_policy', expression='is_public = true'),
        ]


class PermutationModel(RLSModel):
    """Model for testing policy permutations."""
    # Logic is dynamically assigned in tests, but table must exist.
    name = models.CharField(max_length=100)
    
    class Meta:
        app_label = 'tests'


class UserHierarchy(models.Model):
    """Simple adjacency list for user hierarchy."""
    manager = models.ForeignKey(User, related_name='subordinates', on_delete=models.CASCADE)
    subordinate = models.ForeignKey(User, related_name='managers', on_delete=models.CASCADE)
    
    class Meta:
        app_label = 'tests'


class HierarchyData(RLSModel):
    """Data owned by a user, visible to their manager."""
    data = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        app_label = 'tests'
        rls_policies = [
            UserPolicy('owner_access', user_field='owner'),
            CustomPolicy(
                'manager_access', 
                expression="owner_id IN (SELECT subordinate_id FROM tests_userhierarchy WHERE manager_id = current_setting('rls.user_id')::int)"
            )
        ]