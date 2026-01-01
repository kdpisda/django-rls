"""
Enterprise ERP Test: Complex ACLs

Verifies that RLS correctly handles granular, row-level permissions (ACLs)
combined with hierarchical access.
"""
import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test import TransactionTestCase

from django_rls.db.functions import set_rls_context
from tests.models import Department, ERPDocument, UserPermission


@pytest.mark.django_db(transaction=True)
class TestComplexACLs(TransactionTestCase):
    def setUp(self):
        if connection.vendor != "postgresql":
            pytest.skip("Skipping RLS tests: Database is not PostgreSQL")

        # Users
        self.u_owner = User.objects.create_user("dept_owner")
        self.u_spy = User.objects.create_user("spy")
        self.u_random = User.objects.create_user("random")

        # Structure
        self.dept = Department.objects.create(name="Top Secret Lab")
        self.other_dept = Department.objects.create(name="Public Library")

        # RLS Init (required because TransactionTestCase truncates tables but might
        # lose FORCE RLS if not careful, though usually schema is preserved.
        # But we call enable just in case logic depends on it.)
        with connection.cursor() as cursor:
            # We assume migration ran, so policies exist.
            # Just ensure FORCE RLS is on.
            cursor.execute(
                f"ALTER TABLE {ERPDocument._meta.db_table} FORCE ROW LEVEL SECURITY"
            )

        # Create Document (owned by Lab)
        # We need context to insert? Permissive policies:
        # Hierarchy: IN dept tree. ACL: IN permissions.
        # If I am u_owner in dept, I match Hierarchy.
        set_rls_context("tenant_id", self.dept.id, is_local=False)
        set_rls_context("user_id", self.u_owner.id, is_local=False)

        self.doc = ERPDocument.objects.create(
            title="Alien Tech", department=self.dept, classification="top_secret"
        )

    def test_acl_grant_access(self):
        """
        Verify that a user OUTSIDE the hierarchy can be granted access via ACL.
        """
        # 1. Verify "Spy" cannot see document initially
        # Spy is in "Public Library" dept (or no dept).
        set_rls_context("tenant_id", self.other_dept.id, is_local=False)
        set_rls_context("user_id", self.u_spy.id, is_local=False)

        assert ERPDocument.objects.filter(pk=self.doc.pk).exists() is False

        # 2. Grant Access via ACL Table
        # We insert into UserPermission. RLS does not protect UserPermission
        # table in our model (standard model).
        UserPermission.objects.create(
            user=self.u_spy, document_id=self.doc.id, can_view=True
        )

        # 3. Verify Spy CAN see document now
        # Hierarchy Policy: False (Dept mismatch)
        # ACL Policy: True (Row exists)
        # Result: Visible (OR logic)

        # Assert visibility
        assert ERPDocument.objects.filter(pk=self.doc.pk).exists() is True

        # 4. Verify Revocation
        UserPermission.objects.filter(user=self.u_spy).delete()
        assert ERPDocument.objects.filter(pk=self.doc.pk).exists() is False

    def test_mixed_access_modes(self):
        """
        Verify that having multiple means of access works (Union of permissions).
        """
        # Create a user who is BOTH in department AND has ACL.
        # Postgres should handle this fine (OR).

        u_redundant = User.objects.create_user("redundant")
        UserPermission.objects.create(
            user=u_redundant, document_id=self.doc.id, can_view=True
        )

        set_rls_context("tenant_id", self.dept.id, is_local=False)  # Matches Hierarchy
        set_rls_context("user_id", u_redundant.id, is_local=False)  # Matches ACL

        assert ERPDocument.objects.filter(pk=self.doc.pk).exists() is True
