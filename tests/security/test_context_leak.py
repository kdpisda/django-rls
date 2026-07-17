"""
Security Test: Context Leakage via Connection Pools

This test simulates connection pooling behavior to prove that
RLS context persists (leaks) when exceptions occur.
Refactored to use mocks since valid Postgres DB is not guaranteed in CI.
"""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase

from django_rls.middleware import RLSContextMiddleware


class TestContextLeakage(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("django_rls.middleware.RLSContextMiddleware._set_rls_context")
    @patch("django_rls.middleware.RLSContextMiddleware._clear_rls_context")
    def test_exception_leaks_context_logic(self, mock_clear, mock_set):
        """
        Critical Vulnerability Test:
        If a view raises an exception, the middleware MUST still call _clear_rls_context.
        """
        request = self.factory.get("/error")
        request.user = Mock(id=123)

        def error_view(request):
            raise ValueError("Crash inside view")

        middleware = RLSContextMiddleware(error_view)

        try:
            middleware(request)
        except ValueError:
            pass  # Expected crash

        # Assertion: process_exception logic should ensure cleanup

        if not mock_clear.called:
            pytest.fail("Security Failure: Context was NOT cleared after exception!")

        mock_set.assert_called_once()
        mock_clear.assert_called_once()

    @patch("django_rls.middleware.RLSContextMiddleware._set_rls_context")
    @patch("django_rls.middleware.RLSContextMiddleware._clear_rls_context")
    def test_success_clears_context(self, mock_clear, mock_set):
        """Control test: A normal request should clear context."""
        request = self.factory.get("/")
        request.user = Mock(id=456)

        def success_view(request):
            return HttpResponse("OK")

        middleware = RLSContextMiddleware(success_view)
        middleware(request)

        mock_set.assert_called_once()
        mock_clear.assert_called_once()

    @patch("django_rls.middleware.set_rls_context")
    def test_failure_while_setting_context_still_clears(self, mock_set_rls):
        """
        Critical Vulnerability Test (set-phase failure):

        If setting the RLS context partially succeeds and then raises (e.g. the
        tenant lookup or a context processor hits a transient DB error AFTER
        user_id was already written), the middleware MUST still clear the
        context. Because context is session-scoped (set_config(..., false)),
        skipping the clear leaves the value on the physical connection, and the
        NEXT request reusing that connection (CONN_MAX_AGE / PgBouncer) inherits
        a stale user_id -> cross-user data exposure.

        Reproduction: user_id is set, then tenant detection explodes.
        """
        request = self.factory.get("/")
        request.user = Mock(id=777)
        request.session = {}

        middleware = RLSContextMiddleware(lambda r: HttpResponse("OK"))

        with patch.object(
            RLSContextMiddleware,
            "_get_tenant_id",
            side_effect=RuntimeError("tenant backend down"),
        ):
            with pytest.raises(RuntimeError):
                middleware(request)

        # After the request unwinds, user_id MUST have been reset to '' at least
        # once. The vulnerable version never reaches the clear, so no ('user_id',
        # '', ...) call is ever made.
        cleared_user_id = [
            c
            for c in mock_set_rls.call_args_list
            if c.args and c.args[0] == "user_id" and c.args[1] == ""
        ]
        assert cleared_user_id, (
            "Security Failure: user_id was set but never cleared after the "
            "set-phase raised. Stale context leaks to the next request on a "
            "reused connection."
        )

    @patch("django_rls.middleware.set_rls_context")
    def test_clear_scrubs_base_keys_even_when_nothing_tracked(self, mock_set_rls):
        """
        Critical Vulnerability Test (stale-connection scrub):

        An anonymous request sets no context of its own. If it lands on a
        connection where a PRIOR request left rls.user_id set (e.g. that request
        failed to clear), the anonymous request must still scrub the base keys so
        it cannot read the previous user's rows. The clear must therefore reset
        user_id/tenant_id unconditionally, not only the keys THIS request set.
        """
        request = self.factory.get("/")
        request.user = AnonymousUser()
        request.session = {}
        # No 'tenant' attribute -> _get_tenant_id returns None
        if hasattr(request, "tenant"):
            del request.tenant

        middleware = RLSContextMiddleware(lambda r: HttpResponse("OK"))
        middleware(request)

        cleared_keys = {
            c.args[0]
            for c in mock_set_rls.call_args_list
            if c.args and len(c.args) >= 2 and c.args[1] == ""
        }
        assert "user_id" in cleared_keys, (
            "Security Failure: anonymous request did not scrub rls.user_id; "
            "stale context from a prior request on this connection would leak."
        )
        assert (
            "tenant_id" in cleared_keys
        ), "Security Failure: anonymous request did not scrub rls.tenant_id."


@pytest.mark.postgresql
class TestContextLeakEndToEnd(TestCase):
    """
    End-to-end proof against a real PostgreSQL connection that stale RLS
    context does NOT survive on the connection after a failed request.

    Uses the real middleware and the real set/get helpers on Django's
    (single, reused) test connection -- which is exactly the connection-reuse
    condition that leaks in production with CONN_MAX_AGE / PgBouncer.
    """

    def setUp(self):
        self.factory = RequestFactory()
        from django_rls.db.functions import set_rls_context

        # Start from a clean slate on this connection.
        set_rls_context("user_id", "", is_local=False)
        set_rls_context("tenant_id", "", is_local=False)

    def test_set_phase_failure_does_not_leak_user_id_to_next_request(self):
        from django_rls.db.functions import get_rls_context

        # --- Request A: authenticated user 4242, tenant detection blows up
        #     AFTER user_id has been written to the connection. ---
        req_a = self.factory.get("/a")
        req_a.user = Mock(id=4242)
        req_a.session = {}
        mw = RLSContextMiddleware(lambda r: HttpResponse("A"))

        with patch.object(
            RLSContextMiddleware,
            "_get_tenant_id",
            side_effect=RuntimeError("tenant backend down"),
        ):
            with pytest.raises(RuntimeError):
                mw(req_a)

        # The connection must NOT still carry user 4242's id.
        leaked = get_rls_context("user_id")
        assert leaked in (
            None,
            "",
        ), f"user_id={leaked!r} leaked on the connection after a failed request"

        # --- Request B: an anonymous request reusing the same connection must
        #     not observe any user context. ---
        req_b = self.factory.get("/b")
        req_b.user = AnonymousUser()
        req_b.session = {}
        if hasattr(req_b, "tenant"):
            del req_b.tenant

        observed = {}

        def view_b(request):
            observed["user_id"] = get_rls_context("user_id")
            return HttpResponse("B")

        RLSContextMiddleware(view_b)(req_b)
        assert observed["user_id"] in (
            None,
            "",
        ), f"Anonymous request saw leaked user_id={observed['user_id']!r}"
