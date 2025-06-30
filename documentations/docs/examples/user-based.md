---
sidebar_position: 3
---

# User-Based Access Control

Implement fine-grained user-based access control for personal data, documents, and resources.

## User-Owned Resources

The most common pattern is resources owned by individual users:

### Simple User Ownership

```python
from django_rls.models import RLSModel
from django_rls.policies import UserPolicy

class PersonalNote(RLSModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner'),
        ]

class UserProfile(RLSModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField()
    avatar = models.ImageField(upload_to='avatars/')
    is_public = models.BooleanField(default=False)
    
    class Meta:
        rls_policies = [
            # Users can always see their own profile
            UserPolicy('owner_policy', user_field='user'),
            # Others can see if public
            CustomPolicy(
                'public_policy',
                expression='is_public = true'
            ),
        ]
```

## Collaborative Features

### Shared Documents

```python
class Document(RLSModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner'),
        ]

class DocumentShare(RLSModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.CharField(max_length=10, choices=[
        ('view', 'View'),
        ('edit', 'Edit'),
    ])
    shared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        rls_policies = [
            # Document owner can manage shares
            CustomPolicy(
                'owner_can_manage',
                expression="""
                    document_id IN (
                        SELECT id FROM myapp_document 
                        WHERE owner_id = current_setting('rls.user_id')::integer
                    )
                """
            ),
            # Shared users can see their shares
            UserPolicy('shared_user', user_field='shared_with'),
        ]

# Update Document model to include sharing
class Document(RLSModel):
    # ... fields as above
    
    class Meta:
        rls_policies = [
            # Owner access
            UserPolicy('owner_policy', user_field='owner'),
            # Shared access
            CustomPolicy(
                'shared_policy',
                expression="""
                    id IN (
                        SELECT document_id FROM myapp_documentshare
                        WHERE shared_with_id = current_setting('rls.user_id')::integer
                    )
                """
            ),
        ]
```

### Team Collaboration

```python
class Team(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
    ])

class TeamResource(RLSModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        rls_policies = [
            CustomPolicy(
                'team_member_access',
                expression="""
                    team_id IN (
                        SELECT team_id FROM myapp_teammember
                        WHERE user_id = current_setting('rls.user_id')::integer
                    )
                """
            ),
        ]
```

## Hierarchical Access

### Manager-Employee Structure

```python
class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    manager = models.ForeignKey(
        'self', 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        related_name='direct_reports'
    )

class PerformanceReview(RLSModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(Employee, on_delete=models.CASCADE, 
                                related_name='reviews_given')
    content = models.TextField()
    rating = models.IntegerField()
    
    class Meta:
        rls_policies = [
            CustomPolicy(
                'employee_and_manager_access',
                expression="""
                    -- Employee can see their own reviews
                    employee_id IN (
                        SELECT id FROM myapp_employee 
                        WHERE user_id = current_setting('rls.user_id')::integer
                    )
                    OR
                    -- Manager can see their reports' reviews
                    employee_id IN (
                        SELECT id FROM myapp_employee 
                        WHERE manager_id IN (
                            SELECT id FROM myapp_employee 
                            WHERE user_id = current_setting('rls.user_id')::integer
                        )
                    )
                    OR
                    -- Reviewer can see reviews they wrote
                    reviewer_id IN (
                        SELECT id FROM myapp_employee 
                        WHERE user_id = current_setting('rls.user_id')::integer
                    )
                """
            ),
        ]
```

## Privacy Controls

### Granular Privacy Settings

```python
class UserContent(RLSModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    visibility = models.CharField(max_length=20, choices=[
        ('private', 'Private'),
        ('friends', 'Friends Only'),
        ('public', 'Public'),
    ])
    
    class Meta:
        rls_policies = [
            CustomPolicy(
                'visibility_policy',
                expression="""
                    -- Owner always has access
                    owner_id = current_setting('rls.user_id')::integer
                    OR
                    -- Public content
                    visibility = 'public'
                    OR
                    -- Friends only
                    (
                        visibility = 'friends' 
                        AND owner_id IN (
                            SELECT friend_id FROM myapp_friendship 
                            WHERE user_id = current_setting('rls.user_id')::integer
                            AND status = 'accepted'
                        )
                    )
                """
            ),
        ]

class Friendship(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    friend = models.ForeignKey(User, on_delete=models.CASCADE, 
                              related_name='friend_requests')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('blocked', 'Blocked'),
    ])
```

## Admin Override

Sometimes admins need to bypass RLS:

```python
class SupportTicket(RLSModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20)
    assigned_to = models.ForeignKey(
        User, 
        null=True,
        on_delete=models.SET_NULL,
        related_name='assigned_tickets'
    )
    
    class Meta:
        rls_policies = [
            # User can see their own tickets
            UserPolicy('user_policy', user_field='user'),
            # Assigned support staff can see tickets
            UserPolicy('assigned_policy', user_field='assigned_to'),
            # Admins can see all tickets
            CustomPolicy(
                'admin_policy',
                expression="""
                    EXISTS (
                        SELECT 1 FROM auth_user 
                        WHERE id = current_setting('rls.user_id')::integer
                        AND is_staff = true
                    )
                """
            ),
        ]
```

## Implementation Tips

### 1. User Context Helper

```python
from django_rls.db.functions import set_rls_context

class UserContextMixin:
    """Mixin for views that need user context."""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Set additional user context
            set_rls_context('user_role', request.user.profile.role)
            set_rls_context('user_department', request.user.profile.department)
        return super().dispatch(request, *args, **kwargs)
```

### 2. Bulk Operations

```python
@login_required
def bulk_update_documents(request):
    # This will only update documents the user owns
    updated = Document.objects.filter(
        id__in=request.POST.getlist('document_ids')
    ).update(
        updated_at=timezone.now(),
        status='reviewed'
    )
    
    # 'updated' contains only the count of documents actually updated
    messages.success(request, f'Updated {updated} documents')
```

### 3. Performance Optimization

```python
class OptimizedDocument(RLSModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    # ... other fields
    
    class Meta:
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner'),
        ]
        indexes = [
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['owner', 'status']),
        ]
```

## Testing User-Based Access

```python
class UserAccessTest(TestCase):
    def test_user_isolation(self):
        user1 = User.objects.create_user('user1')
        user2 = User.objects.create_user('user2')
        
        # Create documents
        set_rls_context('user_id', user1.id)
        doc1 = Document.objects.create(
            title='User 1 Doc',
            owner=user1
        )
        
        set_rls_context('user_id', user2.id)
        doc2 = Document.objects.create(
            title='User 2 Doc',
            owner=user2
        )
        
        # Test isolation
        set_rls_context('user_id', user1.id)
        visible_docs = Document.objects.all()
        self.assertEqual(visible_docs.count(), 1)
        self.assertEqual(visible_docs.first(), doc1)
```