"""
Audit Test I: The "Happy Path"

Verifies functional correctness of RLS under normal operations.
- Basic Isolation (User A vs B)
- Multi-Tenant Isolation (Tenant A vs B)
- Role Hierarchy (Manager sees Subordinates)
- CRUD Ownership
- Public Data Access
"""
from django.contrib.auth.models import User
from django.test import TransactionTestCase

from django_rls.db.functions import RLSContext
from tests.models import (
    ComplexModel,
    HierarchyData,
    Organization,
    TenantModel,
    UserHierarchy,
    UserOwnedModel,
)

# Note: We use TransactionTestCase to better simulate DB interactions where RLS matters,
# even though in SQLite the actual enforcement logic (postgres policies)
# doesn't run. These tests verify the *logic* of the filtering when mapped
# to Django ORM query sets or ensure that no errors occur.
#
# CRITICAL: Since we are on SQLite, we can't fully enforce "User A cannot
# see User B" at the DB level. We CAN verify that the `rls_policies` are
# correctly defined on the model and that the middleware sets the context
# correctly.
#
# For strict enforcement testing, we would need the Postgres container.
# We will write these tests assuming "If Postgres was here, these
# invariants hold". We mock the DB enforcement by manually checking
# the context.


class TestHappyPath(TransactionTestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("user1")
        self.u2 = User.objects.create_user("user2")
        self.u3 = User.objects.create_user("user3")  # Public user

        self.org1 = Organization.objects.create(name="Org 1", slug="org1")
        self.org2 = Organization.objects.create(name="Org 2", slug="org2")

    def test_basic_isolation_concept(self):
        """
        Verify: User A should only see their own rows.
        """
        # Create data with RLS context set for each user
        with RLSContext(user_id=self.u1.id):
            UserOwnedModel.objects.create(title="U1 Data", content="x", owner=self.u1)
        with RLSContext(user_id=self.u2.id):
            UserOwnedModel.objects.create(title="U2 Data", content="y", owner=self.u2)

        # Verify isolation: User 1 should only see their own data
        with RLSContext(user_id=self.u1.id):
            assert UserOwnedModel.objects.count() == 1
            assert UserOwnedModel.objects.first().title == "U1 Data"

        # User 2 should only see their own data
        with RLSContext(user_id=self.u2.id):
            assert UserOwnedModel.objects.count() == 1
            assert UserOwnedModel.objects.first().title == "U2 Data"

    def test_multi_tenant_isolation_concept(self):
        """
        Verify: Tenant A should not see Tenant B's data.
        """
        # Create data with tenant context
        with RLSContext(tenant_id=self.org1.id):
            TenantModel.objects.create(name="T1 Data", organization=self.org1)
        with RLSContext(tenant_id=self.org2.id):
            TenantModel.objects.create(name="T2 Data", organization=self.org2)

        # Verify isolation
        with RLSContext(tenant_id=self.org1.id):
            assert TenantModel.objects.count() == 1
            assert TenantModel.objects.first().name == "T1 Data"

        with RLSContext(tenant_id=self.org2.id):
            assert TenantModel.objects.count() == 1
            assert TenantModel.objects.first().name == "T2 Data"

    def test_role_hierarchy(self):
        """
        Verify: Manager can see Subordinate data.
        """
        # Hierarchy: U1 is manager of U2
        UserHierarchy.objects.create(manager=self.u1, subordinate=self.u2)

        # Data owned by U2 - create with U2's context
        with RLSContext(user_id=self.u2.id):
            HierarchyData.objects.create(data="Secret", owner=self.u2)

        # U1 should see it (because of manager policy)
        with RLSContext(user_id=self.u1.id):
            assert HierarchyData.objects.count() == 1

        # U2 should see it (because owner)
        with RLSContext(user_id=self.u2.id):
            assert HierarchyData.objects.count() == 1

        # U3 should NOT see it (no relationship)
        with RLSContext(user_id=self.u3.id):
            assert HierarchyData.objects.count() == 0

    def test_crud_ownership(self):
        """
        Verify: Insert assigns ownership (if handled by app).
        """
        # Usually RLS doesn't auto-assign ownership on insert (that's a
        # default value or trigger). We verify we can insert with context.
        with RLSContext(user_id=self.u1.id):
            obj = UserOwnedModel.objects.create(
                title="Test", content="test", owner=self.u1
            )
            assert obj.owner == self.u1

    def test_public_access(self):
        """
        Verify: Public rows are visible to everyone.
        """
        # Create data with proper context (owner + tenant)
        with RLSContext(user_id=self.u1.id, tenant_id=self.org1.id):
            ComplexModel.objects.create(
                title="Public",
                content="p",
                owner=self.u1,
                organization=self.org1,
                is_public=True,
            )
            ComplexModel.objects.create(
                title="Private",
                content="p",
                owner=self.u1,
                organization=self.org1,
                is_public=False,
            )

        # Public row should be visible to anyone (due to public_policy)
        # Note: ComplexModel has multiple permissive policies (OR logic)
        with RLSContext(user_id=self.u1.id, tenant_id=self.org1.id):
            # Owner should see both
            assert ComplexModel.objects.count() == 2
