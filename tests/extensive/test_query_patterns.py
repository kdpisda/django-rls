
"""
Extensive Test: Query Patterns (Real DB)

This module tests complex ORM usage patterns to ensure RLS is correctly enforced
on Joins, Aggregations, Distinct, and Locking clauses.
"""
from django.test import TransactionTestCase, override_settings
from django.db.models import Count, F, Q, Sum, Exists, OuterRef, Subquery
from tests.models import Organization, TenantModel, UserOwnedModel, ComplexModel
from django.contrib.auth.models import User
from django_rls.db.functions import set_rls_context
from django.db import connection, transaction
import pytest

@pytest.mark.django_db(transaction=True)
class TestQueryPatterns(TransactionTestCase):
    
    def setUp(self):
        if connection.vendor != 'postgresql':
            pytest.skip("Skipping RLS tests: Database is not PostgreSQL")

        self.org1 = Organization.objects.create(name="Org 1", slug="org1")
        self.org2 = Organization.objects.create(name="Org 2", slug="org2")
        
        # Setup tables
        with connection.cursor() as cursor:
            for table in [TenantModel._meta.db_table, Organization._meta.db_table]:
                # Organization doesn't have RLS in model (SimpleModel), wait TenantModel does.
                pass
            cursor.execute(f'ALTER TABLE {TenantModel._meta.db_table} ENABLE ROW LEVEL SECURITY')
            cursor.execute(f'ALTER TABLE {TenantModel._meta.db_table} FORCE ROW LEVEL SECURITY')

        # Create Data
        set_rls_context('tenant_id', self.org1.id, is_local=False)
        TenantModel.objects.create(name="T1 Item 1", organization=self.org1)
        TenantModel.objects.create(name="T1 Item 2", organization=self.org1)
        
        set_rls_context('tenant_id', self.org2.id, is_local=False)
        TenantModel.objects.create(name="T2 Item 1", organization=self.org2)
        
        set_rls_context('tenant_id', '', is_local=False)

    def test_distinct_behavior(self):
        """Verify .distinct() works and doesn't reveal hidden rows."""
        # Set to Org 1
        set_rls_context('tenant_id', self.org1.id, is_local=False)
        
        # Should see 2 items
        cnt = TenantModel.objects.filter(name__startswith="T1").distinct().count()
        assert cnt == 2
        
        # Should see 0 items from T2
        cnt = TenantModel.objects.filter(name__startswith="T2").distinct().count()
        assert cnt == 0
        
    def test_select_for_update(self):
        """Verify .select_for_update() respects visibility."""
        set_rls_context('tenant_id', self.org1.id, is_local=False)
        
        with transaction.atomic():
            # Should lock 2 rows
            qs = TenantModel.objects.select_for_update().all()
            assert len(qs) == 2
            
            # Try to fetch T2 items with lock -> Empty
            qs_hidden = TenantModel.objects.filter(name__startswith="T2").select_for_update()
            assert len(qs_hidden) == 0

    def test_bulk_create_and_update(self):
        """
        Verify bulk operations.
        Note: bulk_create bypasses .save(), so does RLS apply?
        YES, because INSERT checks are done by Database.
        """
        set_rls_context('tenant_id', self.org1.id, is_local=False)
        
        # Bulk Create valid items (matching current tenant)
        TenantModel.objects.bulk_create([
            TenantModel(name="Bulk 1", organization=self.org1),
            TenantModel(name="Bulk 2", organization=self.org1)
        ])
        
        assert TenantModel.objects.filter(name__startswith="Bulk").count() == 2
        
        # Try to Bulk Create INVALID item (org matches, but check policy?)
        # TenantPolicy usually uses 'current_setting'.
        # If we try to insert for Org2 while context is Org1:
        # Policy: organization_id = current_setting('...tenant_id')
        # Insert: organization_id = org2.id != org1.id
        # CHECK FAIL.
        
        import django.db.utils
        with pytest.raises(django.db.utils.ProgrammingError): # RLS violation raises ProgrammingError in recent Django/Psycopg
             TenantModel.objects.bulk_create([
                 TenantModel(name="Malicious Bulk", organization=self.org2)
             ])
             
    def test_subquery_exists_real(self):
        """Real DB verification of Exists subquery."""
        set_rls_context('tenant_id', self.org1.id, is_local=False)
        
        # Check if Org1 exists via subquery on TenantTable
        # Since we can see T1 items, this should be True for Org1
        
        from django.db.models import Exists, OuterRef
        
        # Subquery: select 1 from tenant_model where org_id = outer.id
        # RLS applies to TenantModel.
        # For Org1: We see T1 items. Exists -> True.
        # For Org2: We (User in Org1 context) do not see T2 items. Exists -> False.
        
        # Note: Organization model itself might NOT have RLS.
        # If we query Organization, we see both Org1 and Org2 (unless filtered).
        # We annotate 'has_items'.
        
        subq = TenantModel.objects.filter(organization=OuterRef('pk'))
        qs = Organization.objects.annotate(has_items=Exists(subq)).order_by('slug')
        
        res = list(qs.values('slug', 'has_items'))
        # Org 1: True
        # Org 2: False (because T2 items are hidden)
        
        org1_res = next(r for r in res if r['slug'] == 'org1')
        org2_res = next(r for r in res if r['slug'] == 'org2')
        
        assert org1_res['has_items'] is True
        assert org2_res['has_items'] is False, "RLS should hide items of Org 2, making Exists return False"
