"""
Audit Test II: Leakage & Security Vulnerabilities

Focuses on side-channel leaks and standard RLS bypass techniques.
"""
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TransactionTestCase

from django_rls.db.functions import RLSContext
from tests.models import Organization, UserOwnedModel


class TestLeakage(TransactionTestCase):
    def setUp(self):
        self.u1 = User.objects.create_user("u1")
        self.u2 = User.objects.create_user("u2")
        self.org1 = Organization.objects.create(name="org1", slug="org1")

        # User 2 creates a row that U1 shouldn't see
        with RLSContext(user_id=self.u2.id):
            self.hidden_obj = UserOwnedModel.objects.create(
                title="Hidden", content="data", owner=self.u2
            )
            self.hidden_id = self.hidden_obj.id

    def test_update_blindside(self):
        """
        Scenario: User A runs UPDATE table SET val=X WHERE id=HiddenID.
        Check: The operation must report 0 rows affected, and NOT throw specific errors.
        """
        # With RLS enforced, User 1 trying to update User 2's row should affect 0 rows
        with RLSContext(user_id=self.u1.id):
            qs = UserOwnedModel.objects.filter(id=self.hidden_id)
            count = qs.update(title="Hacked")
            # RLS filters out the row, so 0 rows affected
            assert count == 0

        # Verify the row was not changed
        with RLSContext(user_id=self.u2.id):
            obj = UserOwnedModel.objects.get(id=self.hidden_id)
            assert obj.title == "Hidden"  # Unchanged

    def test_existence_leak_insert_duplicate(self):
        """
        Scenario: Insert a row with a PK that already exists (but is hidden).
        Expected: Database error (IntegrityError: Unique Violation).

        In Postgres, does this leak existence? Yes, "Key (id)=(X) already
        exists." RLS does NOT hide the Primary Key uniqueness constraint
        unless using `ON CONFLICT`.

        This is a KNOWN leak in Postgres RLS unless partitioned or UUIDs
        used. We verify that Django propagates the standard IntegrityError.
        """
        with RLSContext(user_id=self.u1.id):
            try:
                with transaction.atomic():
                    UserOwnedModel(
                        id=self.hidden_id, title="Clash", content="x", owner=self.u1
                    ).save(force_insert=True)
                # If we succeed, ID collision didn't happen or we overwrote.
                assert False, "Should have raised IntegrityError"
            except IntegrityError:
                # Confirms that constraints fire regardless of RLS visibility.
                # This IS a side-channel but unavoidable in standard SQL
                # without logic changes (e.g. random UUIDs).
                pass

    def test_aggregate_leakage(self):
        """
        Scenario: Count(*)
        Check: Returns count of visible rows only.
        """
        # Already covered in tests/extensive/test_query_patterns.py
        pass

    def test_returning_clause_leakage(self):
        """
        Scenario: Insert a row we own, but maybe trigger modifies it?
        Or Insert row we DON'T own (if policy allows).
        If I insert a row for User 2 (as User 1) - if policy allows insert
        but not select? Then logic should prevent `returning`.
        """
        pass
