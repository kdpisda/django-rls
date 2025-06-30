"""User-based usage example with complex policies."""

from django.db import models
from django.contrib.auth.models import User

from django_rls.models import RLSModel
from django_rls.policies import UserPolicy, CustomPolicy


class UserProfile(models.Model):
    """Extended user profile."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    is_manager = models.BooleanField(default=False)


class Document(RLSModel):
    """Document with complex access rules."""
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_documents')
    department = models.CharField(max_length=100)
    is_public = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        rls_policies = [
            # Owner can always see their documents
            UserPolicy('document_owner_policy', user_field='owner'),
            # Public documents are visible to all
            CustomPolicy('document_public_policy', expression='is_public = true'),
            # Department managers can see department documents
            CustomPolicy(
                'document_department_policy',
                expression="""
                EXISTS (
                    SELECT 1 FROM user_based_userprofile up
                    JOIN auth_user u ON u.id = up.user_id
                    WHERE u.id = current_setting('rls.user_id')::integer
                    AND up.department = user_based_document.department
                    AND up.is_manager = true
                )
                """
            ),
        ]


class SharedDocument(RLSModel):
    """Document that can be shared with specific users."""
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE)
    can_edit = models.BooleanField(default=False)
    shared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        rls_policies = [
            # Users can see documents shared with them
            UserPolicy('shared_document_policy', user_field='shared_with'),
            # Document owners can see all shares
            CustomPolicy(
                'shared_document_owner_policy',
                expression="""
                EXISTS (
                    SELECT 1 FROM user_based_document d
                    WHERE d.id = user_based_shareddocument.document_id
                    AND d.owner_id = current_setting('rls.user_id')::integer
                )
                """
            ),
        ]