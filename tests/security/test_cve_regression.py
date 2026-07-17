"""
CVE-class regression tests for django-rls.

These do NOT re-test Django/PostgreSQL internals. They pin the library's own
attack surface against the *classes* of vulnerability behind well-known CVEs,
so a future change cannot silently re-introduce one of them into this package.

Surface the library exposes to potentially-tainted input:
  * DDL identifiers  -> policy name, table name, roles, operation, field names
  * DDL values       -> ModelPolicy Q-object values, expression helpers
  * GUC names/values -> set_config()/current_setting() for rls.* context
  * Regex validators -> field/role name validation (ReDoS surface)

Each test names the CVE whose vulnerability class it guards against.
"""

import time

import pytest
from django.db.models import Q
from django.test import SimpleTestCase

from django_rls.exceptions import PolicyError
from django_rls.policies import (
    BasePolicy,
    ModelPolicy,
    TenantPolicy,
    UserPolicy,
)


class TestIdentifierInjection(SimpleTestCase):
    """
    Class: SQL injection through an identifier/keyword that is interpolated
    into SQL rather than parameterized.

    Real-world analogues:
      * CVE-2022-34265 - Django Trunc()/Extract() injection via the `kind`
        lookup name (a keyword spliced into SQL).
      * CVE-2021-35042 - Django QuerySet.order_by() injection via `__`-laden
        column identifiers.
    Here the analogues are the policy `operation` keyword and policy field
    names, both of which reach the DDL as identifiers.
    """

    def test_operation_keyword_is_whitelisted(self):
        # Only ALL/SELECT/INSERT/UPDATE/DELETE may reach `FOR %(operation)s`.
        with pytest.raises(PolicyError):
            UserPolicy("p", user_field="owner", operation="ALL; DROP TABLE users; --")

    def test_field_name_metacharacters_rejected(self):
        payloads = [
            "owner; DROP TABLE users; --",
            "owner') OR ('1'='1",
            'owner"; DELETE FROM users; --',
            "owner id",  # whitespace
            "owner--",
            "1owner",  # cannot start with a digit
            "owner)",
        ]
        for bad in payloads:
            with pytest.raises(PolicyError):
                TenantPolicy("p", tenant_field=bad)
            with pytest.raises(PolicyError):
                UserPolicy("p", user_field=bad)

    def test_legitimate_field_names_accepted(self):
        for good in ["owner", "tenant", "org_id", "_private", "Field2"]:
            # Should not raise.
            UserPolicy("p", user_field=good)


class TestRoleInjection(SimpleTestCase):
    """
    Class: injection through the `TO <roles>` identifier position, which
    cannot be parameterized. Same family as the identifier CVEs above.
    """

    def test_malicious_role_rejected(self):
        for bad in [
            "public; DROP TABLE users; --",
            "app_role) USING (true) --",
            "role'; SELECT 1; --",
        ]:
            with pytest.raises(PolicyError):
                UserPolicy("p", user_field="owner", roles=bad)

    def test_role_list_and_public_accepted(self):
        UserPolicy("p", user_field="owner", roles="PUBLIC")
        UserPolicy("p", user_field="owner", roles="app_reader, app_writer")


class TestValueInjection(SimpleTestCase):
    """
    Class: SQL injection through a *value* that is string-formatted into SQL
    instead of bound as a parameter.

    Real-world analogues:
      * CVE-2020-7471 - Django StringAgg delimiter injection (an unescaped
        value spliced into SQL).
      * CVE-2019-14234 - Django JSONField key injection.
    Here the analogue is ModelPolicy compiling Q-object values into the policy
    USING/WITH CHECK clause.
    """

    def _compiled(self, **filters):
        from tests.models import UserOwnedModel

        policy = ModelPolicy(name="p", filters=Q(**filters))
        return policy.get_compiled_sql(UserOwnedModel).replace("%%%%", "%")

    def test_stringagg_style_delimiter_payload_is_escaped(self):
        # The shape of CVE-2020-7471: a value carrying a quote + SQL tail.
        payload = "','')) OR 1=1 --"
        sql = self._compiled(title=payload)
        expected = (
            '"tests_userownedmodel"."title" = \'' + payload.replace("'", "''") + "'"
        )
        assert sql == expected, f"Value not safely escaped.\nGot: {sql}"

    def test_value_cannot_terminate_statement(self):
        payload = "x'; DROP TABLE tests_userownedmodel; --"
        sql = self._compiled(title=payload)
        expected = (
            '"tests_userownedmodel"."title" = \'' + payload.replace("'", "''") + "'"
        )
        # Exact-match against the safe form + quote-parity: the payload is wholly
        # contained in one literal with doubled internal quotes, so it cannot
        # terminate the CREATE POLICY statement.
        assert sql == expected, f"Value not safely escaped.\nGot: {sql}"
        assert sql.count("'") % 2 == 0, f"Unbalanced quoting (break-out): {sql}"


class TestContextGucInjection(SimpleTestCase):
    """
    Class: injection through a dynamic setting/GUC name or value.

    Real-world analogue:
      * CVE-2018-1058 - unsafe use of settings/search_path in PostgreSQL.
    The library reads/writes rls.* GUCs; the name and value must always be
    bound as parameters, never concatenated into the SQL string.
    """

    def test_set_rls_context_parameterizes_name_and_value(self):
        from unittest.mock import Mock, patch

        from django_rls.db.functions import set_rls_context

        with patch("django_rls.db.functions.connection") as mock_conn:
            cursor = Mock()
            mock_conn.cursor.return_value.__enter__.return_value = cursor

            malicious_key = "user_id'; DROP TABLE users; --"
            malicious_val = "1'; DROP TABLE users; --"
            set_rls_context(malicious_key, malicious_val)

            sql, params = cursor.execute.call_args.args
            # The SQL template must contain only placeholders, no payload.
            assert "DROP TABLE" not in sql
            assert sql.count("%s") == 3
            # Payload travels as bound params (key is namespaced under rls.).
            assert params[0] == f"rls.{malicious_key}"
            assert params[1] == malicious_val

    def test_get_rls_context_parameterizes_name(self):
        from unittest.mock import Mock, patch

        from django_rls.db.functions import get_rls_context

        with patch("django_rls.db.functions.connection") as mock_conn:
            cursor = Mock()
            mock_conn.cursor.return_value.__enter__.return_value = cursor
            cursor.fetchone.return_value = ["x"]

            get_rls_context("tenant_id'; DROP TABLE users; --")
            sql, params = cursor.execute.call_args.args
            assert "DROP TABLE" not in sql
            assert "%s" in sql


class TestRegexReDoS(SimpleTestCase):
    """
    Class: catastrophic-backtracking ReDoS in an input validator (family of
    CVEs such as CVE-2021-33203 / CVE-2019-14235 and the broader Python `re`
    ReDoS class). The field/role validators run on caller-influenced strings,
    so they must be linear-time.
    """

    def test_field_validator_is_linear_on_pathological_input(self):
        policy = UserPolicy("p", user_field="owner")
        pathological = "a" * 100_000 + "!"  # long valid prefix, invalid tail
        start = time.perf_counter()
        with pytest.raises(PolicyError):
            policy.validate_field_name(pathological)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Validator too slow ({elapsed:.3f}s): possible ReDoS"

    def test_role_validator_is_linear_on_pathological_input(self):
        policy = UserPolicy("p", user_field="owner")
        # Trailing '!' is invalid and (unlike whitespace) is not stripped away.
        pathological = "r" * 100_000 + "!"
        start = time.perf_counter()
        with pytest.raises(PolicyError):
            policy.validate_roles(pathological)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"Validator too slow ({elapsed:.3f}s): possible ReDoS"

    def test_validator_patterns_are_anchored(self):
        # Anchoring both ends is what prevents "valid-prefix + junk" bypass.
        assert BasePolicy.FIELD_NAME_PATTERN.pattern.startswith("^")
        assert BasePolicy.FIELD_NAME_PATTERN.pattern.endswith("$")
        assert BasePolicy.ROLE_NAME_PATTERN.pattern.startswith("^")
        assert BasePolicy.ROLE_NAME_PATTERN.pattern.endswith("$")
