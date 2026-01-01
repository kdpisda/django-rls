"""
Enterprise ERP Test: Recursive Hierarchy

Verifies that RLS (Recursive CTEs) correctly handles deep organizational hierarchies.
"""
import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test import TransactionTestCase

from django_rls.db.functions import set_rls_context
from tests.models import Department, ERPDocument


@pytest.mark.django_db(transaction=True)
class TestRecursiveHierarchy(TransactionTestCase):
    def setUp(self):
        if connection.vendor != "postgresql":
            pytest.skip("Skipping RLS tests: Database is not PostgreSQL")

        # Create Users
        self.u_ceo = User.objects.create_user("ceo")
        self.u_vp_eng = User.objects.create_user("vp_eng")
        self.u_backend = User.objects.create_user("backend_lead")
        self.u_sales = User.objects.create_user("vp_sales")

        # Create Tree
        # L1
        self.d_root = Department.objects.create(name="CEO Office")

        # L2
        self.d_eng = Department.objects.create(name="Engineering", parent=self.d_root)
        self.d_sales = Department.objects.create(name="Sales", parent=self.d_root)

        # L3
        self.d_backend = Department.objects.create(name="Backend", parent=self.d_eng)
        self.d_frontend = Department.objects.create(name="Frontend", parent=self.d_eng)

        # Enable RLS on ERPDocument
        with connection.cursor() as cursor:
            # Department model needs no RLS for this test (or maybe simple Tenant?)
            # But ERPDocument DOES.
            cursor.execute(
                f"ALTER TABLE {ERPDocument._meta.db_table} ENABLE ROW LEVEL SECURITY"
            )
            cursor.execute(
                f"ALTER TABLE {ERPDocument._meta.db_table} FORCE ROW LEVEL SECURITY"
            )

    def test_downward_visibility(self):
        """
        Verify that a user context set to a parent department can
        see documents in child departments (Recursive Policy).
        """
        # Create Documents (As System/Superuser effectively)
        # Note: We create them without RLS context first or use empty context if
        # policy allows. But we are in FORCE RLS. So we need to insert them with a
        # valid policy context OR use a superuser. Since we don't have superuser in
        # this test env setup easily
        # (user is usually DB owner which bypasses RLS, but we access via Django conn).
        # Actually RLS is BYPASSED for Table Owner (which Django connection usually is).
        # EXCEPT `enable_rls` sets `FORCE ROW LEVEL SECURITY`.
        # So we must satisfy policies.

        # Insert Docs for Backend
        # To insert, we need a policy.
        # Hierarchy policy says: "doc.dept_id IN (tree from current_tenant)".
        # To insert into Backend (Dept 3), if I set tenant=Backend,
        # Tree = {Backend}. doc.dept=Backend. Match.

        set_rls_context("tenant_id", self.d_backend.id, is_local=False)
        set_rls_context(
            "user_id", self.u_backend.id, is_local=False
        )  # For ACL policy check? No, policies are OR.

        ERPDocument.objects.create(
            title="Backend Architecture",
            department=self.d_backend,
            classification="confidential",
        )

        # Insert Docs for Frontend
        set_rls_context("tenant_id", self.d_frontend.id, is_local=False)
        ERPDocument.objects.create(title="Frontend UI Kit", department=self.d_frontend)

        # Insert Docs for Sales
        set_rls_context("tenant_id", self.d_sales.id, is_local=False)
        ERPDocument.objects.create(title="Q4 Targets", department=self.d_sales)

        # 1. Verify VP Eng Visibility (Dept 2)
        # Should see: Backend, Frontend.
        # Should NOT see: Sales, CEO.
        set_rls_context("tenant_id", self.d_eng.id, is_local=False)

        qs = ERPDocument.objects.all()
        titles = set(qs.values_list("title", flat=True))

        assert "Backend Architecture" in titles
        assert "Frontend UI Kit" in titles
        assert "Q4 Targets" not in titles

        # 2. Verify CEO Visibility (Dept 1)
        # Should see ALL.
        set_rls_context("tenant_id", self.d_root.id, is_local=False)

        qs = ERPDocument.objects.all()
        titles = set(qs.values_list("title", flat=True))

        assert "Backend Architecture" in titles
        assert "Frontend UI Kit" in titles
        assert "Q4 Targets" in titles

        # 3. Verify Backend Lead Visibility (Dept 3)
        # Should see Self (Backend).
        # Should NOT see Frontend (Sibling) or Eng (Parent).
        set_rls_context("tenant_id", self.d_backend.id, is_local=False)

        qs = ERPDocument.objects.all()
        titles = set(qs.values_list("title", flat=True))

        assert "Backend Architecture" in titles
        assert "Frontend UI Kit" not in titles
