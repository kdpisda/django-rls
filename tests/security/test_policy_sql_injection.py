"""
Regression tests: SQL injection via RLS policy DDL.

Ensures payloads like ``'; DROP TABLE abc; --`` cannot reach executable SQL
through policy names, field names, roles, CustomPolicy expressions, or
ModelPolicy compilation.
"""

from unittest.mock import Mock

import pytest
from django.db import models
from django.db.models import Q

from django_rls.backends.postgresql.base import RLSDatabaseSchemaEditor
from django_rls.exceptions import PolicyError
from django_rls.models import RLSModel
from django_rls.policies import CustomPolicy, ModelPolicy, TenantPolicy, UserPolicy

CUSTOM_POLICY_BLOCKED = [
    "is_public = true; DROP TABLE abc;",
    "is_public = true; drop table abc; --",
    "1=1; TRUNCATE users",
    "1=1; ALTER TABLE users DISABLE ROW LEVEL SECURITY",
    "1=1; CREATE TABLE evil (id int)",
    "1=1; GRANT ALL ON users TO public",
    "1=1; REVOKE ALL ON users FROM public",
    "1=1; COPY users TO '/tmp/leak'",
    "owner_id = 1 -- bypass",
    "owner_id = 1 /* comment */ OR true",
]

CUSTOM_POLICY_ALLOWED = [
    "is_public = true",
    "created_at > CURRENT_DATE - INTERVAL '30 days'",
    "name != 'hidden'",
    (
        "department_id IN ("
        "WITH RECURSIVE dept_tree AS ("
        "    SELECT id FROM tests_department WHERE id = 1 "
        "    UNION SELECT d.id FROM tests_department d "
        "    INNER JOIN dept_tree dt ON d.parent_id = dt.id"
        ") SELECT id FROM dept_tree)"
    ),
    (
        "(user_id = NULLIF(current_setting('rls.user_id', true), '')::integer "
        "OR is_public = true)"
    ),
]

INVALID_FIELD_NAMES = [
    "tenant'; DELETE FROM users WHERE '1'='1",
    "owner; DROP TABLE abc",
    "user_id' OR '1'='1",
    "1evil",
]

INVALID_ROLES = [
    "public; DROP TABLE users",
    "authenticated, evil; DROP TABLE x",
    "role'name",
    "123role",
]


def _sql_contains_escaped_literal(sql: str, raw_value: str) -> bool:
    """True when *raw_value* appears as a properly doubled-quote SQL literal."""
    return f"'{raw_value.replace(chr(39), chr(39) * 2)}'" in sql


class _StringFilterModel(RLSModel):
    title = models.CharField(max_length=200)
    label = models.CharField(max_length=200)

    class Meta:
        app_label = "tests"
        rls_policies = []


@pytest.mark.security
@pytest.mark.parametrize("expression", CUSTOM_POLICY_BLOCKED)
def test_custom_policy_blocks_dangerous_expressions(expression):
    with pytest.raises(PolicyError, match="forbidden SQL tokens"):
        CustomPolicy("blocked_policy", expression=expression)


@pytest.mark.security
@pytest.mark.parametrize("expression", CUSTOM_POLICY_ALLOWED)
def test_custom_policy_allows_safe_expressions(expression):
    policy = CustomPolicy("safe_policy", expression=expression)
    assert policy.get_sql_expression() == expression


@pytest.mark.security
def test_policy_name_is_quoted_in_ddl():
    editor = RLSDatabaseSchemaEditor(Mock())
    editor.execute = Mock()
    editor.quote_name = lambda name: f'"{name}"'

    malicious_name = "test'; DROP TABLE users; --"
    policy = UserPolicy(malicious_name, user_field="owner")
    model = Mock()
    model._meta.db_table = "test_table"

    editor.create_policy(model, policy)

    sql = editor.execute.call_args[0][0]
    assert 'CREATE POLICY "test\'; DROP TABLE users; --" ON "test_table"' in sql
    assert "USING (owner_id" in sql


@pytest.mark.security
def test_table_name_is_quoted_in_enable_rls():
    editor = RLSDatabaseSchemaEditor(Mock())
    editor.execute = Mock()
    editor.quote_name = lambda name: f'"{name}"'

    model = Mock()
    model._meta.db_table = "users'; DROP TABLE sensitive_data; --"
    editor.enable_rls(model)

    sql = editor.execute.call_args[0][0]
    assert '"users\'; DROP TABLE sensitive_data; --"' in sql
    assert "ALTER TABLE" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql


@pytest.mark.security
@pytest.mark.parametrize("field_name", INVALID_FIELD_NAMES)
def test_invalid_field_names_rejected(field_name):
    with pytest.raises(PolicyError, match="Invalid field name"):
        TenantPolicy("tenant_policy", tenant_field=field_name)


@pytest.mark.security
@pytest.mark.parametrize("roles", INVALID_ROLES)
def test_invalid_policy_roles_rejected(roles):
    with pytest.raises(PolicyError, match="Invalid role name|roles must"):
        UserPolicy("role_policy", user_field="owner", roles=roles)


@pytest.mark.security
def test_public_role_is_allowed():
    policy = UserPolicy("public_role", user_field="owner", roles="PUBLIC")
    assert policy.roles == "PUBLIC"


@pytest.mark.security
def test_model_policy_escapes_string_literal_quotes():
    malicious = "'; DROP TABLE users; --"
    policy = ModelPolicy("title_filter", filters=Q(title=malicious))
    sql = policy.get_compiled_sql(_StringFilterModel)

    assert _sql_contains_escaped_literal(sql, malicious)


@pytest.mark.security
def test_model_policy_combo_filters_escape_injection():
    policy = ModelPolicy(
        "combo",
        filters=Q(title="safe") | Q(label="also'; DROP TABLE t; --"),
    )
    sql = policy.get_compiled_sql(_StringFilterModel)
    assert _sql_contains_escaped_literal(sql, "also'; DROP TABLE t; --")
