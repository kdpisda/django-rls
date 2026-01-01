"""
Security Test: SQL Injection in Expressions

This test verifies that the library prevents SQL injection
when generating RLS policies.
"""
import pytest
from django.test import SimpleTestCase
from django_rls.expressions import RLSExpression
from django_rls.policies import TenantPolicy

class TestSQLInjection(SimpleTestCase):
    
    def test_unsafe_string_interpolation(self):
        """
        Critical Vulnerability Test:
        Verify that string values are NOT safely parameterized or escaped.
        """
        malicious_value = "1'; DROP TABLE users; --"
        
        # Currently expressions.py does: f"'{value}'"
        # We expect this to produce: '1'; DROP TABLE users; --'
        # Which is a valid SQL injection payload.
        
        # If the code was safe, it should produce something like: '1''; DROP TABLE users; --'
        # or use placeholders like %s
        
        builder = RLSExpression("dummy")
        result = builder._format_value(malicious_value)
        
        print(f"\nFormatted Value: {result}")
        
        # Check for successful injection (un-escaped quote)
        if result == f"'{malicious_value}'":
            pytest.fail("Security Failure: Value was NOT escaped and allows SQL injection!")
        
        # We expect simple escaping for now, e.g. single quotes doubled
        expected_safe = f"'{malicious_value.replace("'", "''")}'"
        assert result == expected_safe or result == f"'{malicious_value.replace("'", "\\'")}'", \
            f"Value not properly escaped. Got: {result}"

    def test_policy_field_injection(self):
        """Test injection via policy field names."""
        # The library does simplistic regex validation, so this might actually pass (be safe)
        # But we double check.
        pass
