
"""
Integration Test: SQL Policy Audit

Verifies that defining an RLSModel actually creates the corresponding policies
in the PostgreSQL catalog (pg_policy).
"""
import pytest
from django.test import TransactionTestCase
from django.db import connection, migrations, models
from django.db.migrations.executor import MigrationExecutor
from django_rls.models import RLSModel
from django_rls.policies import TenantPolicy, UserPolicy
from django.apps import apps
from django.contrib.auth.models import User

# Define a dynamic test model for this test
# We do this inside the test file but outside the class to allow Django to pick it up if needed,
# or we use SchemaEditor to create it properly.

@pytest.mark.django_db(transaction=True)
class TestPolicyAudit(TransactionTestCase):

    def setUp(self):
        if connection.vendor != 'postgresql':
            pytest.skip("Skipping SQL Audit: Database is not PostgreSQL")

    def test_policy_creation_in_catalog(self):
        """
        Verify that `enable_rls()` creates entries in `pg_policy`.
        """
        table_name = 'audit_test_model'
        
        # 1. Define Model
        class AuditModel(RLSModel):
            name = models.CharField(max_length=100)
            tenant = models.ForeignKey('tests.Organization', on_delete=models.CASCADE)
            
            class Meta:
                app_label = 'tests'
                db_table = table_name
                rls_policies = [
                    TenantPolicy('audit_tenant_policy', tenant_field='tenant')
                ]

        # 2. Create Table via Schema Editor
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(AuditModel)
        
        try:
            # 3. Trigger RLS Enablement (normally done via post_migrate)
            # We call it manually to simulate the signal handling
            AuditModel.enable_rls()
            
            # 4. Audit PostgreSQL Catalog
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT polname, polcmd, polpermissive 
                    FROM pg_policy 
                    WHERE polrelid = %s::regclass
                """, [table_name])
                
                rows = cursor.fetchall()
                
                # We expect 1 policy: 'audit_tenant_policy'
                # polcmd: 'r' (SELECT) ? No, usually ALL ('*') or specific chars. 
                # cmd column in pg_policy is 'polcmd' type char:
                # r=SELECT, a=INSERT, w=UPDATE, d=DELETE, *=ALL.
                # 'audit_tenant_policy' is FOR ALL.
                
                print(f"DEBUG: Found policies: {rows}")
                
                policy_names = [r[0] for r in rows]
                assert 'audit_tenant_policy' in policy_names
                
                # Verify properties
                # (name, cmd, permissive)
                # cmd should be '*' (ALL) by default for our Policy class
                # permissive should be True (permissive) by default
                
                target_p = next(r for r in rows if r[0] == 'audit_tenant_policy')
                assert target_p[2] is True, "Policy should be PERMISSIVE"
                # polcmd is tricky to assert as char without looking up specific Postgres version implementation details
                # but we verified existence.
                
        finally:
            # Cleanup
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(AuditModel)

    def test_policy_teardown_in_catalog(self):
        """
        Verify that `disable_rls()` removes entries from `pg_policy`.
        """
        table_name = 'audit_teardown_model'
        
        class AuditTeardownModel(RLSModel):
            name = models.CharField(max_length=100)
            user = models.ForeignKey(User, on_delete=models.CASCADE)
            
            class Meta:
                app_label = 'tests'
                db_table = table_name
                rls_policies = [
                    UserPolicy('audit_user_policy', user_field='user')
                ]

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(AuditTeardownModel)
            
        try:
            AuditTeardownModel.enable_rls()
            
            # Verify created
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_policy WHERE polrelid = %s::regclass", [table_name])
                assert cursor.fetchone()[0] == 1
                
            # Disable
            AuditTeardownModel.disable_rls()
            
            # Verify removed
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_policy WHERE polrelid = %s::regclass", [table_name])
                assert cursor.fetchone()[0] == 0
                
        finally:
             with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(AuditTeardownModel)

    def test_post_migrate_signal_integration(self):
        """
        Verify that the post_migrate signal calls enable_rls automatically.
        We can't easily run a full migration here without messing up test state,
        but we can check if existing models (like TenantModel) have policies in DB.
        """
        # TenantModel is created by migrations in standard test setup.
        # Its policies should exist in pg_policy.
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT polname FROM pg_policy 
                WHERE polrelid = 'tests_tenantmodel'::regclass
            """)
            rows = cursor.fetchall()
            names = [r[0] for r in rows]
            
            assert 'org_policy' in names, "TenantModel policy should exist from test suite migrations"
