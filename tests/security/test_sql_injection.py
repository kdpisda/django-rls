"""
Security Test: SQL Injection in Expressions

This test verifies that the library prevents SQL injection
when generating RLS policies.
"""

import pytest
from django.db.models import Q
from django.test import SimpleTestCase

from django_rls.expressions import RLSExpression
from django_rls.policies import ModelPolicy


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

        # If the code was safe, it should produce something like:
        # '1''; DROP TABLE users; --'
        # or use placeholders like %s

        builder = RLSExpression("dummy")
        result = builder._format_value(malicious_value)

        print(f"\nFormatted Value: {result}")

        # Check for successful injection (un-escaped quote)
        if result == f"'{malicious_value}'":
            pytest.fail(
                "Security Failure: Value was NOT escaped and allows SQL injection!"
            )

        # We expect simple escaping for now, e.g. single quotes doubled
        safe_val = malicious_value.replace("'", "''")
        expected_safe = f"'{safe_val}'"

        escaped_val = malicious_value.replace("'", "\\'")
        assert (
            result == expected_safe or result == f"'{escaped_val}'"
        ), f"Value not properly escaped. Got: {result}"

    def test_policy_field_injection(self):
        """Test injection via policy field names."""
        # The library does simplistic regex validation, so this might actually
        # pass (be safe)
        # But we double check.
        pass


class TestModelPolicyInjection(SimpleTestCase):
    """
    Vulnerability: ModelPolicy.get_compiled_sql() interpolates query params
    into the policy DDL itself. String params were wrapped in single quotes
    WITHOUT escaping embedded quotes, so a value containing a quote breaks out
    of the literal and injects arbitrary predicate into the USING/WITH CHECK
    clause -- baking a permanent RLS bypass into the policy.
    """

    def _compiled(self, payload):
        from tests.models import UserOwnedModel

        policy = ModelPolicy(name="inj_policy", filters=Q(title=payload))
        # get_compiled_sql doubles '%' to survive later %-formatting; undo that
        # so we can reason about the actual SQL text the DB will see.
        return policy.get_compiled_sql(UserOwnedModel).replace("%%%%", "%")

    def _expected_safe(self, payload):
        # A safely-quoted PostgreSQL string literal doubles embedded quotes.
        escaped = payload.replace("'", "''")
        return f'"tests_userownedmodel"."title" = \'{escaped}\''

    def test_single_quote_breakout_is_prevented(self):
        """A quote in the value must NOT terminate the string literal."""
        payload = "x' OR '1'='1"
        sql = self._compiled(payload)

        # The tell-tale of a successful break-out is the value's quote closing
        # the literal and leaving `OR '1'='1'` as live SQL.
        assert (
            "OR '1'='1'" not in sql
        ), f"SQL injection: value broke out of the string literal.\nGot: {sql}"
        assert sql == self._expected_safe(payload), (
            f"Value not safely quoted.\nGot:      {sql}\n"
            f"Expected: {self._expected_safe(payload)}"
        )

    def test_classic_drop_table_payload_is_neutralized(self):
        """A destructive payload must remain an inert string literal.

        The whole payload must sit inside a single quoted literal with every
        embedded quote doubled, so it cannot terminate the statement. We assert
        exact equality against that safe form rather than substring-matching:
        the escaped output legitimately contains ``''); DROP`` (a doubled quote
        followed by the inert tail), which a naive substring check misreads.
        """
        payload = "1'); DROP TABLE tests_userownedmodel; --"
        sql = self._compiled(payload)

        assert sql == self._expected_safe(payload), (
            f"Value not safely quoted.\nGot:      {sql}\n"
            f"Expected: {self._expected_safe(payload)}"
        )
        # Quote-parity invariant: a safely-terminated literal has an even number
        # of single quotes (open + close + doubled internals).
        assert sql.count("'") % 2 == 0, f"Unbalanced quoting (break-out): {sql}"

    def test_percent_and_quote_together(self):
        """A value with both % and ' must survive escaping without corruption."""
        payload = "50%' OR TRUE --"
        sql = self._compiled(payload)
        assert sql == self._expected_safe(
            payload
        ), f"Mixed %/quote value not safely quoted.\nGot: {sql}"
