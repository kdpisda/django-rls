"""Basic usage example."""

from django.db import models
from django.contrib.auth.models import User

from django_rls.models import RLSModel
from django_rls.policies import UserPolicy


class UserDocument(RLSModel):
    """Document that belongs to a user."""
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        rls_policies = [
            UserPolicy('user_document_policy', user_field='user'),
        ]
    
    def __str__(self):
        return self.title