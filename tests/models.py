"""
Test models for Django RLS.

These models are only used in tests.
"""
from django.contrib.auth.models import User
from django.db import models

from django_rls.models import RLSModel
from django_rls.policies import CustomPolicy, TenantPolicy, UserPolicy


class Organization(models.Model):
    """Test organization model."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        app_label = "tests"


class SimpleModel(models.Model):
    """Simple model without RLS."""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "tests"


class UserOwnedModel(RLSModel):
    """Model with user-based RLS."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "tests"
        rls_policies = [
            UserPolicy("owner_policy", user_field="owner"),
        ]


class TenantModel(RLSModel):
    """Model with tenant-based RLS."""

    name = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "tests"
        rls_policies = [
            TenantPolicy("org_policy", tenant_field="organization"),
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
        app_label = "tests"
        rls_policies = [
            UserPolicy("owner_policy", user_field="owner"),
            TenantPolicy("org_policy", tenant_field="organization"),
            CustomPolicy("public_policy", expression="is_public = true"),
        ]


class PermutationModel(RLSModel):
    """Model for testing policy permutations."""

    # Logic is dynamically assigned in tests, but table must exist.
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "tests"


class UserHierarchy(models.Model):
    """Simple adjacency list for user hierarchy."""

    manager = models.ForeignKey(
        User, related_name="subordinates", on_delete=models.CASCADE
    )
    subordinate = models.ForeignKey(
        User, related_name="managers", on_delete=models.CASCADE
    )

    class Meta:
        app_label = "tests"


class HierarchyData(RLSModel):
    """Data owned by a user, visible to their manager."""

    data = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        app_label = "tests"
        rls_policies = [
            UserPolicy("owner_access", user_field="owner"),
            CustomPolicy(
                "manager_access",
                expression=(
                    "owner_id IN (SELECT subordinate_id FROM tests_userhierarchy "
                    "WHERE manager_id = current_setting('rls.user_id')::int)"
                ),
            ),
        ]


class Department(models.Model):
    """ERP Department with hierarchical structure."""

    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="sub_departments",
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = "tests"


class UserPermission(models.Model):
    """Granular ACL table for users and documents."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Generic or specific FK to object? For testing, we verify ERPDocument access.
    document_id = models.IntegerField()
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)

    class Meta:
        app_label = "tests"


class ERPDocument(RLSModel):
    """Document with complex RLS: Hierarchy + ACLs."""

    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    classification = models.CharField(
        max_length=20, default="public"
    )  # public, confidential

    class Meta:
        app_label = "tests"
        rls_policies = [
            # 1. Hierarchy Policy:
            # Visible if User's Dept is ancestor of Document's Dept.
            # OR if in same Dept.
            # SQL: department_id IN (
            #    WITH RECURSIVE dept_tree AS (
            #        SELECT id FROM tests_department
            #        WHERE id = current_setting('rls.tenant_id')::int
            #        UNION
            #        SELECT d.id FROM tests_department d
            #        INNER JOIN dept_tree dt ON d.parent_id = dt.id
            #    )
            #    SELECT id FROM dept_tree
            # )
            CustomPolicy(
                "hierarchy_policy",
                expression="department_id IN ("
                "WITH RECURSIVE dept_tree AS ("
                "    SELECT id FROM tests_department "
                "    WHERE id = current_setting('rls.tenant_id')::int "
                "    UNION "
                "    SELECT d.id FROM tests_department d "
                "    INNER JOIN dept_tree dt ON d.parent_id = dt.id "
                ") "
                "SELECT id FROM dept_tree"
                ")",
            ),
            # 2. ACL Policy:
            # Visible if User has explicit entry in UserPermission for this doc.
            # SQL: id IN (
            #    SELECT document_id FROM tests_userpermission
            #    WHERE user_id = current_setting('rls.user_id')::int AND can_view = true
            # )
            CustomPolicy(
                "acl_policy",
                expression="id IN ("
                "    SELECT document_id FROM tests_userpermission "
                "    WHERE user_id = current_setting('rls.user_id')::int "
                "    AND can_view = true"
                ")",
            ),
        ]
