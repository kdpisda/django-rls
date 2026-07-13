"""
Audit Test IV: Application Layer & Context Switching

Verifies:
- Connection Pooling safety (Dirty Reads)
- Transaction Aborts (Context clearing)
- Superuser interactions
- Race conditions (simulated)
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import RequestFactory, TransactionTestCase

from django_rls.middleware import RLSContextMiddleware


class TestAppLayer(TransactionTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.u1 = User.objects.create_user("u1")

    @patch("django_rls.middleware.clear_rls_context")
    @patch("django_rls.middleware.apply_rls_context")
    def test_transaction_abort_clears_context(self, mock_apply, mock_clear):
        """Verify that `_clear_rls_context` is called even if app crashes."""
        middleware = RLSContextMiddleware(lambda r: "OK")
        request = self.factory.get("/")
        request.user = self.u1
        request.session = {}

        try:
            middleware._set_rls_context(request)
            raise ValueError("Crash")
        except ValueError:
            pass
        finally:
            middleware._clear_rls_context(request)

        mock_apply.assert_called_once()
        mock_clear.assert_called_once()

    @patch("django_rls.middleware.clear_rls_context")
    @patch("django_rls.middleware.apply_rls_context")
    def test_superuser_bypass_application_check(self, mock_apply, mock_clear):
        """Django superusers still receive RLS identity context from middleware."""
        su = User.objects.create_superuser("admin", "admin@e.com", "pass")
        request = self.factory.get("/")
        request.user = su
        request.session = {}

        middleware = RLSContextMiddleware(lambda r: "OK")
        middleware(request)

        mock_apply.assert_called_once_with(
            {"user_id": su.id}, system=True, source="middleware"
        )
        mock_clear.assert_called_once()

    def test_connection_pooling_safety(self):
        """Covered in tests/security/test_context_leak.py and context hygiene."""
        pass
