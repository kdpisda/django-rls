---
sidebar_position: 3
---

# User-Based Access Control

Implement fine-grained user-based access control for personal data, documents, and resources.

## User-Owned Resources

The most common pattern is resources owned by individual users:

### Simple User Ownership

```python
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django_rls.models import RLSModel
from django_rls.policies import ModelPolicy, RLS

class PersonalNote(RLSModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        rls_policies = [
            # Standard "View Own Data" pattern
            ModelPolicy('owner_policy', filters=Q(owner=RLS.user_id()))
        ]

class UserProfile(RLSModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField()
    avatar = models.ImageField(upload_to='avatars/')
    is_public = models.BooleanField(default=False)

    class Meta:
        rls_policies = [
            # Owner can see profile OR Anyone can see if public
            ModelPolicy(
                'access_policy',
                filters=(
                    Q(user=RLS.user_id()) |
                    Q(is_public=True)
                )
            )
        ]
```

## Collaborative Features

### Shared Documents

Implement Google Docs-style sharing using relations.

```python
class Document(RLSModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        rls_policies = [
            # Access if Owner OR if shared via DocumentShare
            ModelPolicy(
                'access_policy',
                filters=(
                    Q(owner=RLS.user_id()) |
                    Q(documentshare__shared_with=RLS.user_id()) # Automatic EXISTS subquery!
                )
            )
        ]

class DocumentShare(RLSModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.CharField(max_length=10, choices=[('view', 'View'), ('edit', 'Edit')])

    class Meta:
        rls_policies = [
            # Visibility:
            # 1. Document Owner can see shares (to manage them)
            # 2. The Shared User can see their own share entry
            ModelPolicy(
                'share_visibility',
                filters=(
                    Q(document__owner=RLS.user_id()) |  # Owner of the parent doc
                    Q(shared_with=RLS.user_id())        # The user it's shared with
                )
            )
        ]
```

### Team Collaboration

Team members access resources based on membership.

```python
class Team(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class TeamResource(RLSModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    class Meta:
        rls_policies = [
            # Access if current user is a member of the resource's team
            ModelPolicy(
                'team_access',
                filters=Q(team__teammember__user=RLS.user_id())
            )
        ]
```
*Note: `django-rls` automatically converts the `team__teammember__user` lookup into an efficient `EXISTS` subquery.*

## Hierarchical Access

### Manager-Employee Structure

```python
class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

class PerformanceReview(RLSModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reviews_given')
    content = models.TextField()

    class Meta:
        rls_policies = [
            ModelPolicy(
                'review_visibility',
                filters=(
                    # 1. Employee sees own review
                    Q(employee__user=RLS.user_id()) |

                    # 2. Manager sees their direct reports' reviews
                    Q(employee__manager__user=RLS.user_id()) |

                    # 3. Reviewer sees reviews they wrote
                    Q(reviewer__user=RLS.user_id())
                )
            )
        ]
```

## Privacy Controls

### Granular Privacy Settings

```python
class UserContent(RLSModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    visibility = models.CharField(max_length=20, choices=[
        ('private', 'Private'),
        ('friends', 'Friends Only'),
        ('public', 'Public'),
    ])

    class Meta:
        rls_policies = [
            ModelPolicy(
                'privacy_policy',
                filters=(
                    Q(owner=RLS.user_id()) |            # Owner
                    Q(visibility='public') |            # Public
                    (
                        Q(visibility='friends') &       # Friends Only
                        Q(owner__friendship__friend=RLS.user_id(),
                          owner__friendship__status='accepted')
                    )
                )
            )
        ]
```

## Admin Override

Sometimes admins need to bypass standard rules.

```python
class SupportTicket(RLSModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # ... fields

    class Meta:
        rls_policies = [
            ModelPolicy(
                'access_policy',
                filters=(
                    Q(user=RLS.user_id()) |             # Ticket Owner
                    Q(assigned_to=RLS.user_id()) |      # Assigned Staff
                    Q(RLS.context('user_is_staff') == 'true') # Global Admin Override
                )
            )
        ]
```

## Implementation Tips

### 1. User Context Helper

To support custom context like `user_is_staff`, use a Context Processor:

```python
# settings.py
RLS_CONTEXT_PROCESSORS = [
    'myapp.context.user_role_context'
]

# myapp/context.py
def user_role_context(request):
    if request.user.is_authenticated:
        return {
            'user_is_staff': str(request.user.is_staff).lower()
        }
    return {}
```

### 2. Indexes

Always index fields used in lookups for performance:

```python
class OptimizedDocument(RLSModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['owner', '-created_at']),
        ]
```
