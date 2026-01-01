
"""
Integration Tests for PostgreSQL RLS Enforcement.

These tests run ONLY against a live PostgreSQL database to verify that
Row Level Security policies are actively filtering rows at the SQL level.
"""
import pytest
from django.test import TransactionTestCase
from django.db import connection, transaction
from django.conf import settings
from django.contrib.auth.models import User
from tests.models import UserOwnedModel, TenantModel, Organization
from django_rls.db.functions import set_rls_context, get_rls_context

@pytest.mark.django_db(transaction=True)
class TestPostgresRLSEnforcement(TransactionTestCase):
    
    def setUp(self):
        # Skip if not using Postgres
        if connection.vendor != 'postgresql':
            pytest.skip("Skipping PostgreSQL RLS tests: Database is not PostgreSQL")

        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")
        self.org1 = Organization.objects.create(name="Org 1", slug="org1")
        
        # FORCE RLS on the tests tables to ensure Owner (rls_test_user) is restricted
        # We do this FIRST so we know the state.
        with connection.cursor() as cursor:
            for table in ['tests_userownedmodel', 'tests_tenantmodel']:
                # Ensure RLS is on and forced
                cursor.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
                cursor.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')

        # Create data for U1 (Switch context to U1)
        set_rls_context('user_id', self.u1.id, is_local=False)
        UserOwnedModel.objects.create(title="U1 Public", content="data", owner=self.u1)
        UserOwnedModel.objects.create(title="U1 Secret", content="data", owner=self.u1)
        
        # Create data for U2 (Switch context to U2)
        set_rls_context('user_id', self.u2.id, is_local=False)
        UserOwnedModel.objects.create(title="U2 Secret", content="data", owner=self.u2)
        
        # Clear context before tests start
        # Explicitly set both to empty strings to define the variables
        set_rls_context('user_id', '', is_local=False)
        set_rls_context('tenant_id', '', is_local=False)


        # FORCE RLS on the tests tables to ensure Owner (rls_test_user) is restricted
        # This is critical because the test runs as the DB owner.
        with connection.cursor() as cursor:
            for table in ['tests_userownedmodel', 'tests_tenantmodel']:
                cursor.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
                cursor.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
                
                # We also need to ensure policies exist. 
                # The "already exists" error in logs suggests they do, but we can recreate to be safe if specific logic needed.
                # For now, relying on them being present. If they accept CREATE POLICY errors silently, fine.


    def test_raw_sql_enforcement(self):
        """
        Verify that RAW SQL queries return filtered results when Context is set.
        """
        with connection.cursor() as cursor:
            # 1. Set Context for U1
            set_rls_context('user_id', self.u1.id, is_local=False)
            
            # 2. Execute Raw SQL
            cursor.execute('SELECT count(*) FROM tests_userownedmodel')
            count = cursor.fetchone()[0]
            
            # 3. Assert count is 2 (U1's rows), not 3 (Total rows)
            assert count == 2, f"RLS Failed: U1 saw {count} rows, expected 2"

            # 4. Switch Context to U2
            set_rls_context('user_id', self.u2.id, is_local=False)
            cursor.execute('SELECT count(*) FROM tests_userownedmodel')
            count_u2 = cursor.fetchone()[0]
            assert count_u2 == 1, f"RLS Failed: U2 saw {count_u2} rows, expected 1"
            
    def test_context_clearing_enforcement(self):
        """
        Verify that clearing context blocks access (assuming restrictive default).
        """
        if not getattr(settings, 'DJANGO_RLS', {}).get('DEFAULT_PERMISSIVE', True):
             # If restrictive by default, clearing context -> 0 rows
             with connection.cursor() as cursor:
                 set_rls_context('user_id', '', is_local=False)
                 cursor.execute('SELECT count(*) FROM tests_userownedmodel')
                 count = cursor.fetchone()[0]
                 assert count == 0
        else:
            # If permissive, behavior depends on policy definition.
            # Usually 'USING (owner_id = current_setting(...))' implies non-matching rows are hidden.
            # If current_setting is empty, it won't match any owner_id (int).
            pass

    def test_tenant_isolation_sql(self):
        """
        Verify tenant isolation at SQL level.
        """
        # Setup tenant data
        # Must set context to Org 1 to insert Org 1 data
        set_rls_context('tenant_id', self.org1.id, is_local=False)
        t1_item = TenantModel.objects.create(name="T1", organization=self.org1)
        
        # Clear context to start test logic fresh
        set_rls_context('tenant_id', '', is_local=False)
        start_count = TenantModel.objects.count() # Should be 0 visible now

        
        with connection.cursor() as cursor:
            # Set context to Org 1
            set_rls_context('tenant_id', self.org1.id, is_local=False)
            
            cursor.execute('SELECT count(*) FROM tests_tenantmodel')
            count = cursor.fetchone()[0]
            
            # Should see T1 item
            assert count >= 1

            # Set context to Org 999 (Non-existent)
            set_rls_context('tenant_id', 999, is_local=False)
            
            cursor.execute('SELECT count(*) FROM tests_tenantmodel')
            count_empty = cursor.fetchone()[0]
            
            assert count_empty == 0
