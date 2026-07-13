"""
Stress Test: Concurrency and Thread Safety

Exercises middleware against a live PostgreSQL connection.
"""
import threading
import time
from unittest.mock import Mock, patch

import pytest
from django.db import close_old_connections, connection, connections
from django.http import HttpResponse
from django.test import RequestFactory, TransactionTestCase

from django_rls.db.functions import get_rls_context
from django_rls.middleware import RLSContextMiddleware


class TestConcurrency(TransactionTestCase):
    databases = {"default"}

    def setUp(self):
        self.factory = RequestFactory()
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL required")

    def test_sequential_requests_isolate_context_on_postgres(self):
        """Each request sets and clears its own RLS identity on PostgreSQL."""
        seen = {}

        def capture_view(request):
            seen["user_id"] = get_rls_context("user_id")
            seen["tenant_id"] = get_rls_context("tenant_id")
            return HttpResponse("OK")

        middleware = RLSContextMiddleware(capture_view)

        for worker_id in range(20):
            seen.clear()
            request = self.factory.get(f"/tenant/{worker_id}")
            request.user = Mock(id=worker_id * 100, spec=[])
            request.session = {}
            with patch.object(middleware, "_get_tenant_id", return_value=worker_id):
                middleware(request)

            assert seen["user_id"] == str(worker_id * 100)
            assert seen["tenant_id"] == str(worker_id)
            assert get_rls_context("user_id") in (None, "")
            assert get_rls_context("tenant_id") in (None, "")

    def test_concurrent_requests_complete_on_postgres(self):
        """
        Concurrent workers must complete without error on a live database.

        PostgreSQL session variables are per-connection; under heavy overlap
        workers may share pool timing. This test asserts stability, not that
        fifty threads can safely multiplex one session variable namespace.
        """
        connections["default"].inc_thread_sharing()
        completed = []
        errors = []
        lock = threading.Lock()

        def slow_view(_request):
            time.sleep(0.01)
            return HttpResponse("OK")

        middleware = RLSContextMiddleware(slow_view)

        def client_worker(worker_id, tenant_id, user_id):
            try:
                close_old_connections()
                request = self.factory.get(f"/tenant/{tenant_id}")
                request.user = Mock(id=user_id, spec=[])
                request.session = {}
                with patch.object(
                    middleware, "_get_tenant_id", return_value=tenant_id
                ):
                    middleware(request)
                with lock:
                    completed.append(worker_id)
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [
            threading.Thread(target=client_worker, args=(i, i, i * 100))
            for i in range(50)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        connections["default"].dec_thread_sharing()

        if errors:
            pytest.fail(f"Concurrency errors occurred: {errors}")
        assert len(completed) == 50

    def test_middleware_is_stateless(self):
        """Verify middleware does not store request-specific state on self."""
        middleware = RLSContextMiddleware(lambda r: HttpResponse("OK"))
        request = self.factory.get("/")
        request.user = Mock(id=1, spec=[])
        request.session = {}

        initial_attrs = set(dir(middleware))
        middleware(request)
        final_attrs = set(dir(middleware))

        unsafe_attrs = [
            a for a in (final_attrs - initial_attrs) if not a.startswith("__")
        ]
        if unsafe_attrs:
            pytest.fail(f"Middleware is NOT stateless! It stored: {unsafe_attrs}")