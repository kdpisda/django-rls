
"""
Integration Test: SQL Policy Updates

Verifies that modifying a policy in the model definition and re-running enable_rls
(simulating a migration) updates the existing policy in the database instead of failing.
"""
import pytest
from django.test import TransactionTestCase
from django.db import connection, models
from django_rls.models import RLSModel
from django_rls.policies import CustomPolicy

@pytest.mark.django_db(transaction=True)
class TestPolicyUpdates(TransactionTestCase):

    def setUp(self):
        if connection.vendor != 'postgresql':
            pytest.skip("Skipping SQL Audit: Database is not PostgreSQL")

    def test_policy_update_reflection(self):
        """
        Verify that changing a policy expression updates the SQL in pg_policy.
        """
        table_name = 'update_test_model'
        
        # 1. Define initial model state
        class UpdateModel(RLSModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'tests'
                db_table = table_name
                # Initial Policy: name != 'hidden'
                rls_policies = [
                    CustomPolicy('update_policy', expression="name != 'hidden'")
                ]

        # 2. Create Table
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(UpdateModel)
            
        try:
            # 3. Enable RLS (Initial Creation)
            UpdateModel.enable_rls()
            
            # Verify Initial State
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pg_get_expr(polqual, polrelid) 
                    FROM pg_policy 
                    WHERE polname = 'update_policy' 
                    AND polrelid = %s::regclass
                """, [table_name])
                initial_expr = cursor.fetchone()[0]
                # Postgres normalizes SQL, e.g. ((name)::text <> 'hidden'::text)
                assert 'hidden' in initial_expr
                
            # 4. Modify Policy Definition
            # We modify the class attribute directly to simulate a code change + reload
            UpdateModel._rls_policies = [
                CustomPolicy('update_policy', expression="name != 'secret'")
            ]
            
            # 5. Re-run Enable RLS (Simulate post_migrate)
            # This SHOULD update the policy using ALTER POLICY, not fail.
            UpdateModel.enable_rls()
            
            # 6. Verify Updated State
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pg_get_expr(polqual, polrelid) 
                    FROM pg_policy 
                    WHERE polname = 'update_policy' 
                    AND polrelid = %s::regclass
                """, [table_name])
                updated_expr = cursor.fetchone()[0]
                
                print(f"DEBUG: Updated Expr: {updated_expr}")
                assert 'secret' in updated_expr
                assert 'hidden' not in updated_expr
                
        finally:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(UpdateModel)
