
"""
Extensive Test: Policy Permutations (Real DB Verification)

This module tests the logic of combining multiple policies using a live PostgreSQL database.
"""
import pytest
from django.test import TransactionTestCase
from django.db import connection
from django.contrib.auth.models import User
from tests.models import ComplexModel, Organization
from django_rls.db.functions import set_rls_context, get_rls_context

@pytest.mark.django_db(transaction=True)
class TestPolicyPermutations(TransactionTestCase):
    
    def setUp(self):
        # Ensure we are on Postgres
        if connection.vendor != 'postgresql':
            pytest.skip("Skipping RLS tests: Database is not PostgreSQL")
            
        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")
        self.org1 = Organization.objects.create(name="Org 1", slug="org1")
        self.org2 = Organization.objects.create(name="Org 2", slug="org2")

        # Force RLS for ComplexModel
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE tests_complexmodel ENABLE ROW LEVEL SECURITY')
            cursor.execute('ALTER TABLE tests_complexmodel FORCE ROW LEVEL SECURITY')
    
    def _create_item(self, title, user, org, public=False, content="stuff"):
        # Simulate data creation by switching context to valid values temporarily
        # or using superuser if we had one. Since we don't, we impersonate the user.
        
        # We need to satisfy checks. 
        # ComplexModel has: UserPolicy(owner), TenantPolicy(org), CustomPolicy(is_public)
        # If is_public=True, anyone can see? 
        # Postgres default: Policies are OR'd.
        # So "owner=me" OR "org=my_org" OR "is_public=true"
        # To INSERT, we need to pass CHECK on at least one?
        # Actually, WITH CHECK is also OR'd.
        
        set_rls_context('user_id', user.id, is_local=False)
        set_rls_context('tenant_id', org.id, is_local=False)
        
        obj = ComplexModel.objects.create(
            title=title, content=content,
            owner=user, organization=org,
            is_public=public
        )
        
        set_rls_context('user_id', '', is_local=False)
        set_rls_context('tenant_id', '', is_local=False)
        return obj

    def test_combined_policies_or_logic(self):
        """
        Verify that multiple policies are combined with OR logic.
        ComplexModel has UserPolicy OR TenantPolicy OR Custom((public)).
        """
        # Create Item: U1, Org1, Private
        i1 = self._create_item("I1", self.u1, self.org1, False)
        
        # Create Item: U2, Org1, Private
        i2 = self._create_item("I2", self.u2, self.org1, False)
        
        # Create Item: U2, Org2, Public
        i3 = self._create_item("I3", self.u2, self.org2, True)

        # 1. As U1 in Org2
        # - Should see I1 (Owner Match)? Yes.
        # - Should see I2 (Org Match)? No (Org1 != Org2).
        # - Should see I3 (Public Match)? Yes.
        
        with connection.cursor() as cursor:
            set_rls_context('user_id', self.u1.id, is_local=False)
            set_rls_context('tenant_id', self.org2.id, is_local=False)
            
            qs = ComplexModel.objects.all()
            ids = set(qs.values_list('title', flat=True))
            
            assert 'I1' in ids, "Should see owned item (UserPolicy)"
            assert 'I3' in ids, "Should see public item (CustomPolicy)"
            assert 'I2' not in ids, "Should NOT see U2/Org1 item"
            assert len(ids) == 2

    def test_restrictive_policy_logic(self):
        """
        Verify RESTRICTIVE policies are combined with AND logic.
        We will manually add a RESTRICTIVE policy via SQL since the model definition 
        defaults to PERMISSIVE.
        """
        # Add a restrictive policy: "content != 'bad'"
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE POLICY "restrict_bad_content" ON tests_complexmodel
                AS RESTRICTIVE
                FOR ALL
                TO public
                USING (content != 'bad')
            """)
        
        # If restrictive policy works, NOTHING should be seen.
        # If ignored, we see Good and Bad.

        # Create Item: U1, Org1, content='good'
        i1 = self._create_item("Good", self.u1, self.org1, False, content="good")
        
        # Create Item: U1, Org1, content='bad'
        # Restrictive policy "content != 'bad'" should BLOCK this insert with WITH CHECK
        import django.db.utils
        with pytest.raises(django.db.utils.ProgrammingError):
             i2 = self._create_item("Bad", self.u1, self.org1, False, content="bad")
        
        # As U1, Org1:
        # Permissive policies allow both.
        # Restrictive policy blocks 'bad'.
        # Result: See 'Good', don't see 'Bad' (because it doesn't exist!)
        
        qs = ComplexModel.objects.all()
        titles = list(qs.values_list('title', flat=True))
        
        assert 'Good' in titles
        assert 'Bad' not in titles
        
        # Clean up policy manually? Or let transaction rollback handle it?
        # TransactionTestCase wraps in transaction, but DDL (CREATE POLICY) in Postgres
        # is transactional, so it should rollback.
