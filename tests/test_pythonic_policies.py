"""
Test Suite: Pythonic Policies (Q Objects)

Verifies that ModelPolicy correctly compiles Django Q objects into RLS SQL.
"""
import pytest
from django.contrib.auth.models import User
from django.db import connection, models
from django.db.models import Q
from django.test import TransactionTestCase

from django_rls.models import RLSModel
from django_rls.policies import RLS, ModelPolicy


@pytest.mark.django_db(transaction=True)
class TestPythonicPolicies(TransactionTestCase):
    def setUp(self):
        if connection.vendor != "postgresql":
            pytest.skip("Skipping RLS tests: Database is not PostgreSQL")

    def test_basic_compilation(self):
        """
        Verify simple Q object compilation.
        """

        class SimpleQModel(RLSModel):
            status = models.CharField(max_length=20)

            class Meta:
                app_label = "tests"
                db_table = "simple_q_model"
                rls_policies = [
                    ModelPolicy("status_policy", filters=Q(status="active"))
                ]

        # Create Table
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(SimpleQModel)

        try:
            # Enable RLS
            SimpleQModel.enable_rls()

            # Verify SQL in Catalog
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_get_expr(polqual, polrelid)
                    FROM pg_policy
                    WHERE polname = 'status_policy'
                    AND polrelid = 'simple_q_model'::regclass
                """
                )
                expr = cursor.fetchone()[0]
                # Expected: status = 'active' (postgres format)
                # Postgres might normalize to (status)::text = 'active'::text
                assert "status" in expr
                assert "active" in expr

        finally:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(SimpleQModel)

    def test_rls_context_helper(self):
        """
        Verify RLS.user_id() compilation.
        """

        class ContextModel(RLSModel):
            owner = models.ForeignKey(User, on_delete=models.CASCADE)

            class Meta:
                app_label = "tests"
                db_table = "context_q_model"
                rls_policies = [
                    ModelPolicy("owner_access", filters=Q(owner=RLS.user_id()))
                ]

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(ContextModel)

        try:
            ContextModel.enable_rls()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_get_expr(polqual, polrelid)
                    FROM pg_policy
                    WHERE polname = 'owner_access'
                    AND polrelid = 'context_q_model'::regclass
                """
                )
                expr = cursor.fetchone()[0]
                # Expected:
                # owner_id = NULLIF(current_setting('rls.user_id', true), '')::integer
                assert "rls.user_id" in expr
                assert "current_setting" in expr

        finally:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(ContextModel)

    def test_complex_logic(self):
        """
        Verify OR/AND logic.
        """

        class ComplexQModel(RLSModel):
            is_public = models.BooleanField(default=False)
            tenant_id = models.IntegerField()

            class Meta:
                app_label = "tests"
                db_table = "complex_q_model"
                rls_policies = [
                    ModelPolicy(
                        "access_logic",
                        filters=Q(is_public=True) | Q(tenant_id=RLS.tenant_id()),
                    )
                ]

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(ComplexQModel)

        try:
            ComplexQModel.enable_rls()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_get_expr(polqual, polrelid)
                    FROM pg_policy
                    WHERE polname = 'access_logic'
                    AND polrelid = 'complex_q_model'::regclass
                """
                )
                expr = cursor.fetchone()[0]
                print(f"DEBUG EXPR: {expr}")
                # OR logic check
                assert "OR" in expr or "or" in expr
                assert "is_public" in expr
                assert "rls.tenant_id" in expr

        finally:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(ComplexQModel)

    def test_policy_enforcement(self):
        """
        Verify that the generated policy actually enforces access control on data.
        """

        class EnforcedModel(RLSModel):
            secret_code = models.CharField(max_length=10)

            class Meta:
                app_label = "tests"
                db_table = "enforced_model"
                rls_policies = [
                    ModelPolicy("secret_filter", filters=Q(secret_code="open"))
                ]

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(EnforcedModel)

        try:
            # 1. Enable RLS
            EnforcedModel.enable_rls()

            # 2. Insert Data (Bypassing RLS or usually owner bypasses,
            # but let's assume we are testing SELECT)
            # We need to use raw SQL or ensure we can leverage the policy?
            # Actually, owner (rls_test_user) bypasses RLS by default unless
            # force_rls is used. But wait, create_model uses default connection.

            with connection.cursor() as cursor:
                cursor.execute(
                    f"ALTER TABLE {EnforcedModel._meta.db_table} FORCE ROW LEVEL "
                    f"SECURITY"
                )

            # 3. Operations
            # Case A: Compliant Data
            # Should be allowed (assuming PERMISSIVE policy allows it)
            # AND assuming we have NO other blocking policies.
            # RLS default is: if any policy matches, row is visible.
            # If NO policy matches, row is invisible.

            # Insert 'open' (Matches Policy)
            EnforcedModel.objects.create(secret_code="open")

            # Insert 'closed' (Does NOT match)
            # With FORCE RLS, simple INSERT might fail if it violates policy?
            # Or it inserts but is invisible?
            # Postgres default: INSERT checks WITH CHECK.
            # Our policies have WITH CHECK by default.

            # So 'closed' should fail ProgrammingError/CheckViolation.
            from django.db import utils

            with pytest.raises(
                utils.ProgrammingError
            ):  # InsufficientPrivilege / Check violation
                EnforcedModel.objects.create(secret_code="closed")

            # 4. Verify Visibility
            # Should see 1 row ('open')
            assert EnforcedModel.objects.count() == 1
            assert EnforcedModel.objects.first().secret_code == "open"

        finally:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(EnforcedModel)
