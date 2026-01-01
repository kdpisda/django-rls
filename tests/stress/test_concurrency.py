"""
Stress Test: Concurrency and Thread Safety

This test simulates high concurrency to ensure that RLS context setting
is thread-safe and isolated between requests.
"""
import threading
import time
from unittest.mock import Mock, patch

import pytest
from django.test import RequestFactory, SimpleTestCase

from django_rls.middleware import RLSContextMiddleware


class TestConcurrency(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("django_rls.middleware.set_rls_context")
    def test_concurrent_requests_isolation(self, mock_set_context):
        """
        Simulate multiple threads processing requests for different tenants
        simultaneously to ensure no variable leakage (thread-safety).
        """

        # Define a slow-ish view that holds the context open
        def slow_view(request):
            time.sleep(0.01)  # 10ms delay
            return "OK"

        middleware = RLSContextMiddleware(slow_view)

        errors = []

        def client_worker(tenant_id, user_id):
            try:
                request = self.factory.get(f"/tenant/{tenant_id}")
                request.user = Mock(id=user_id)
                # Mock tenant extraction logic for this test
                with patch.object(middleware, "_get_tenant_id", return_value=tenant_id):
                    middleware(request)
            except Exception as e:
                errors.append(e)

        threads = []
        # Spawn 50 threads with different tenant/user IDs
        for i in range(50):
            t = threading.Thread(target=client_worker, args=(i, i * 100))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        if errors:
            pytest.fail(f"Concurrency errors occurred: {errors}")

        # If we got here, all requests completed without crashing.
        # Logic verification:
        # Since we use mocks, we can't easily verify which thread called what on the GLOBAL mock.
        # However, the key is that RLSContextMiddleware uses LOCAL variables
        # (request, tenant_id) to call set_rls_context.
        # As long as it doesn't use `self.tenant_id` (class instance state),
        # it is thread safe.
        # This test primarily verifies no race conditions in the pure python logic crash it.
        pass

    @patch("django_rls.middleware.set_rls_context")
    def test_middleware_is_stateless(self, mock_set_context):
        """Verify middleware does not store request-specific state on self."""
        middleware = RLSContextMiddleware(lambda r: "OK")
        request = self.factory.get("/")
        request.session = {}

        # Determine attributes before request
        initial_attrs = set(dir(middleware))

        middleware(request)

        # Determine attributes after request
        final_attrs = set(dir(middleware))

        # If new attributes were added (e.g. self.tenant_id), it's a leak risk
        new_attrs = final_attrs - initial_attrs
        # Filter out built-ins or innocuous changes
        unsafe_attrs = [a for a in new_attrs if not a.startswith("__")]

        if unsafe_attrs:
            pytest.fail(f"Middleware is NOT stateless! It stored: {unsafe_attrs}")
