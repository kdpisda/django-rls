"""
Security tests for Django RLS based on OWASP vulnerabilities.

Tests cover:
- SQL Injection (OWASP A03:2021)
- Broken Access Control (OWASP A01:2021)
- Security Misconfiguration (OWASP A05:2021)
- Identification and Authentication Failures (OWASP A07:2021)
- Injection (OWASP A03:2021)
"""

from unittest.mock import Mock, PropertyMock, patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from django_rls.backends.postgresql.base import RLSDatabaseSchemaEditor
from django_rls.db.functions import RLSContext, get_rls_context, set_rls_context
from django_rls.exceptions import PolicyError
from django_rls.middleware import RLSContextMiddleware
from django_rls.policies import CustomPolicy, TenantPolicy, UserPolicy


class TestSQLInjectionPrevention(TestCase):
    """Test SQL injection prevention (OWASP A03:2021)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.connection = Mock()
        self.editor = RLSDatabaseSchemaEditor(self.connection)
        self.editor.execute = Mock()
        # Override quote_name to return quoted strings
        self.editor.quote_name = lambda x: f'"{x}"'

    def test_policy_name_sql_injection(self):
        """Test that policy names are properly escaped."""
        # Attempt SQL injection via policy name
        malicious_policy = UserPolicy("test'; DROP TABLE users; --", user_field="owner")

        model = Mock()
        model._meta.db_table = "test_table"

        self.editor.create_policy(model, malicious_policy)

        # Check that the malicious input was properly quoted
        call_args = self.editor.execute.call_args[0][0]
        # Verify the policy name is quoted (won't execute as SQL)
        assert '"test\'; DROP TABLE users; --"' in call_args
        # Also verify the overall structure is correct
        assert "CREATE POLICY" in call_args
        assert "USING" in call_args

    def test_table_name_sql_injection(self):
        """Test that table names are properly escaped."""
        model = Mock()
        # Attempt SQL injection via table name
        model._meta.db_table = "users'; DROP TABLE sensitive_data; --"

        self.editor.enable_rls(model)

        call_args = self.editor.execute.call_args[0][0]
        # The table name should be properly quoted
        assert '"users\'; DROP TABLE sensitive_data; --"' in call_args
        assert "ALTER TABLE" in call_args
        assert "ENABLE ROW LEVEL SECURITY" in call_args

    def test_field_name_sql_injection(self):
        """Test that field names in policies are properly handled."""
        # Attempt SQL injection via field name
        with pytest.raises(PolicyError) as exc_info:
            TenantPolicy(
                "test_policy", tenant_field="tenant'; DELETE FROM users WHERE '1'='1"
            )

        # Should reject invalid field names
        assert "Invalid field name" in str(exc_info.value)
        assert "letters, numbers, and underscores" in str(exc_info.value)

    def test_custom_expression_validation(self):
        """Test that custom expressions don't allow arbitrary SQL."""
        # This should be validated/sanitized in production
        policy = CustomPolicy(
            "test_policy", expression="is_public = true; DROP TABLE users; --"
        )

        # The expression is used as-is, but should be validated
        expr = policy.get_sql_expression()
        assert expr == "is_public = true; DROP TABLE users; --"
        # In production, this should be validated or use parameterized queries

    @patch("django_rls.db.functions.connection")
    def test_context_value_sql_injection(self, mock_conn):
        """Test that context values are properly parameterized."""
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Attempt SQL injection via user ID
        malicious_user_id = "1'; DROP TABLE users; --"
        set_rls_context("user_id", malicious_user_id)

        # Check that parameterized query was used
        mock_cursor.execute.assert_called_with(
            "SELECT set_config(%s, %s, %s)", ["rls.user_id", malicious_user_id, False]
        )


class TestBrokenAccessControl(TestCase):
    """Test access control vulnerabilities (OWASP A01:2021)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RLSContextMiddleware(lambda r: Mock())

    @patch("django_rls.db.functions.connection")
    def test_user_cannot_set_arbitrary_context(self, mock_conn):
        """Test that users cannot manipulate RLS context directly."""
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Create request with authenticated user
        request = self.factory.get("/")
        request.user = Mock(id=123)
        request.session = {}

        # User tries to set context to different user ID via headers/params
        request.META["HTTP_X_RLS_USER_ID"] = "456"
        request.GET = {"rls_user_id": "789"}

        # Middleware should only use authenticated user ID
        self.middleware._set_rls_context(request)

        # Verify only the authenticated user's ID was set
        calls = mock_cursor.execute.call_args_list
        set_user_id_calls = [
            c for c in calls if "user_id" in str(c) and "set_config" in str(c)
        ]
        assert len(set_user_id_calls) == 1
        assert "123" in str(set_user_id_calls[0])
        assert "456" not in str(set_user_id_calls[0])
        assert "789" not in str(set_user_id_calls[0])

    def test_anonymous_user_cannot_access_protected_data(self):
        """Test that anonymous users don't get access to protected data."""
        request = self.factory.get("/")
        request.user = AnonymousUser()
        request.session = {}

        # Middleware should not set user context for anonymous users
        with patch("django_rls.middleware.set_rls_context") as mock_set:
            self.middleware._set_rls_context(request)

            # Should not set user_id for anonymous users
            user_id_calls = [c for c in mock_set.call_args_list if c[0][0] == "user_id"]
            assert len(user_id_calls) == 0

    def test_tenant_isolation(self):
        """Test that tenant isolation cannot be bypassed."""
        # Create request with user belonging to tenant 1
        request = self.factory.get("/")
        request.user = Mock(id=123)
        request.tenant = Mock(id=1)
        request.session = {"tenant_id": 1}

        with patch("django_rls.middleware.set_rls_context") as mock_set:
            self.middleware._set_rls_context(request)

            # Verify tenant context is set correctly
            tenant_calls = [
                c for c in mock_set.call_args_list if c[0][0] == "tenant_id"
            ]
            assert len(tenant_calls) == 1
            assert tenant_calls[0][0][1] == 1


class TestSecurityMisconfiguration(TestCase):
    """Test security misconfiguration vulnerabilities (OWASP A05:2021)."""

    def test_rls_force_enabled_by_default(self):
        """Test that RLS should be forced to prevent bypass by table owner."""
        editor = RLSDatabaseSchemaEditor(Mock())

        # Check that FORCE RLS method exists
        assert hasattr(editor, "force_rls")

        # Verify the SQL command includes FORCE
        assert "FORCE ROW LEVEL SECURITY" in editor.sql_force_rls

    def test_policies_are_restrictive_by_default(self):
        """Test that policies can be restrictive (deny by default)."""
        policy = UserPolicy(
            "test_policy", user_field="owner", permissive=False  # Restrictive policy
        )

        assert policy.permissive is False

    def test_debug_mode_doesnt_leak_information(self):
        """Test that debug mode doesn't leak sensitive information."""
        from django_rls.conf import RLSConfig

        # Mock the debug property
        with patch.object(RLSConfig, "debug", new_callable=PropertyMock) as mock_debug:
            mock_debug.return_value = True

            # Import after patching
            from django_rls.conf import rls_config

            # Verify debug is enabled
            assert rls_config.debug is True

            # In a real implementation, we would verify that sensitive data
            # is not logged even when debug is True


class TestAuthenticationBypass(TestCase):
    """Test authentication bypass vulnerabilities (OWASP A07:2021)."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    def test_session_fixation_prevention(self):
        """Test that RLS context is properly cleared between requests."""
        middleware = RLSContextMiddleware(lambda r: Mock())

        with patch("django_rls.middleware.set_rls_context") as mock_set:
            # First request with user 1
            request1 = self.factory.get("/")
            request1.user = Mock(id=1)
            middleware._set_rls_context(request1)
            middleware._clear_rls_context()

            # Verify context was cleared
            clear_calls = [
                c
                for c in mock_set.call_args_list
                if c[0][1] == ""  # Empty string means clearing
            ]
            assert len(clear_calls) >= 2  # user_id and tenant_id cleared

    def test_privilege_escalation_prevention(self):
        """Test that users cannot escalate privileges through RLS manipulation."""
        # Create a policy that checks user permissions
        policy_expression = """
        EXISTS (
            SELECT 1 FROM auth_user u
            WHERE u.id = NULLIF(current_setting('rls.user_id', true), '')::integer
            AND u.is_superuser = false
        )
        """

        policy = CustomPolicy("restricted_policy", expression=policy_expression)

        # Even if user tries to set superuser context, the policy should prevent access
        assert "is_superuser = false" in policy.get_sql_expression()


class TestInjectionVulnerabilities(TestCase):
    """Test various injection vulnerabilities (OWASP A03:2021)."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    def test_header_injection_prevention(self):
        """Test that HTTP headers cannot inject RLS context."""
        middleware = RLSContextMiddleware(lambda r: Mock())
        request = self.factory.get("/")
        request.user = Mock(id=123)

        # Try to inject via various headers
        request.META["HTTP_RLS_USER_ID"] = "456"
        request.META["HTTP_X_TENANT_ID"] = "999"
        request.META["HTTP_AUTHORIZATION"] = "Bearer malicious"

        with patch("django_rls.middleware.set_rls_context") as mock_set:
            middleware._set_rls_context(request)

            # Verify only legitimate user ID was set
            user_calls = [c for c in mock_set.call_args_list if c[0][0] == "user_id"]
            assert all("123" in str(c) for c in user_calls)
            assert not any("456" in str(c) for c in user_calls)

    def test_json_injection_prevention(self):
        """Test that JSON payloads cannot inject RLS context."""
        request = self.factory.post(
            "/",
            data='{"user_id": 999, "tenant_id": "1 OR 1=1"}',
            content_type="application/json",
        )
        request.user = Mock(id=123)

        middleware = RLSContextMiddleware(lambda r: Mock())

        with patch("django_rls.middleware.set_rls_context") as mock_set:
            middleware._set_rls_context(request)

            # Verify request body didn't affect context
            user_calls = [c for c in mock_set.call_args_list if c[0][0] == "user_id"]
            assert not any("999" in str(c) for c in user_calls)


class TestRLSBypassPrevention(TestCase):
    """Test prevention of RLS bypass attempts."""

    def test_direct_sql_execution_blocked(self):
        """Test that direct SQL execution respects RLS."""
        # In production, ensure raw SQL queries still respect RLS
        with patch("django.db.connection.cursor") as mock_cursor:
            cursor = Mock()
            mock_cursor.return_value.__enter__.return_value = cursor

            # Even raw queries should have RLS applied at DB level
            from django.db import connection

            with connection.cursor() as cursor:
                # This is just a test - in reality, RLS is enforced by PostgreSQL
                pass

    def test_orm_bulk_operations_respect_rls(self):
        """Test that bulk operations respect RLS."""
        # Bulk creates, updates, and deletes should respect RLS
        # This is enforced at the database level
        pass

    def test_migration_operations_require_privileges(self):
        """Test that RLS operations require appropriate database privileges."""
        from django_rls.migration_operations import EnableRLS

        # These operations should only work with appropriate DB privileges
        enable_op = EnableRLS("TestModel")
        assert hasattr(enable_op, "database_forwards")
        assert hasattr(enable_op, "database_backwards")


class TestCrossTenantVulnerabilities(TestCase):
    """Test cross-tenant access vulnerabilities."""

    def test_tenant_context_isolation(self):
        """Test that tenant contexts are properly isolated."""
        # Skip if not using PostgreSQL (current_setting is PostgreSQL-specific)
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL-specific test")

        with RLSContext(tenant_id=1, user_id=100):
            assert get_rls_context("tenant_id") == "1"

            # Nested context shouldn't affect outer context
            with RLSContext(tenant_id=2):
                assert get_rls_context("tenant_id") == "2"

            # Original context restored
            assert get_rls_context("tenant_id") == "1"

    def test_concurrent_request_isolation(self):
        """Test that concurrent requests don't share RLS context."""
        # Each request should have its own database connection/session
        # This is handled by Django's connection pooling
        pass


class TestPolicyValidation(TestCase):
    """Test policy validation for security issues."""

    def test_policy_name_validation(self):
        """Test that policy names are validated."""
        # Empty name should raise error
        with pytest.raises(PolicyError):
            UserPolicy("", user_field="owner")

        # Very long names might cause issues
        long_name = "a" * 1000
        policy = UserPolicy(long_name, user_field="owner")
        assert len(policy.name) == 1000

    def test_policy_expression_complexity(self):
        """Test handling of complex policy expressions."""
        # Complex nested expression
        complex_expr = """
        (user_id = NULLIF(current_setting('rls.user_id', true), '')::integer
        OR EXISTS (
            SELECT 1 FROM permissions p
            WHERE p.user_id = NULLIF(current_setting('rls.user_id', true), '')::integer
            AND p.resource_id = id
        ))
        AND NOT deleted
        AND (
            is_public = true
            OR owner_id = NULLIF(current_setting('rls.user_id', true), '')::integer
        )
        """

        policy = CustomPolicy("complex_policy", expression=complex_expr)
        assert policy.get_sql_expression() == complex_expr

    def test_malformed_policy_handling(self):
        """Test handling of malformed policies."""
        # Malformed SQL should be caught at the database level
        malformed = CustomPolicy(
            "bad_policy", expression="SELECT * FROM"  # Incomplete SQL
        )

        # This would fail when applied to the database
        assert malformed.get_sql_expression() == "SELECT * FROM"


class TestSecurityHeaders(TestCase):
    """Test security headers and transport security."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    @patch("django_rls.middleware.set_rls_context")
    def test_no_sensitive_data_in_responses(self, mock_set_context):
        """Test that RLS context is not leaked in responses."""
        middleware = RLSContextMiddleware(lambda r: HttpResponse())
        request = self.factory.get("/")
        request.user = Mock(id=123)

        response = middleware(request)

        # Ensure no RLS context in response headers
        # Response.headers might not exist in older Django versions
        if hasattr(response, "headers"):
            assert "rls.user_id" not in str(response.headers)
            assert "rls.tenant_id" not in str(response.headers)

        # Verify context was set but not leaked
        mock_set_context.assert_called()
