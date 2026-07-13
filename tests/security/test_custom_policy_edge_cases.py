"""
Regression tests: CustomPolicy edge cases and known limitations.

Documents blocklist coverage, quote-break tautologies (developer-supplied SQL),
and DDL embedding behavior.
"""

from unittest.mock import Mock

import pytest

from django_rls.backends.postgresql.base import RLSDatabaseSchemaEditor
from django_rls.exceptions import PolicyError
from django_rls.policies import CustomPolicy

CUSTOM_POLICY_DML_BLOCKED = [
    "EXISTS (SELECT 1 FROM users WHERE DELETE FROM users IS NOT NULL)",
    "owner_id IN (SELECT id FROM users UNION ALL SELECT id FROM users WHERE UPDATE = true)",
    "1=1 OR (INSERT INTO audit DEFAULT VALUES) IS NOT NULL",
]

CUSTOM_POLICY_KNOWN_LIMITATIONS = [
    "owner_id = 1' OR '1'='1",
    "owner_id = 1 OR 1=1",
    "is_public = true OR owner_id != owner_id",
    "name = '' OR '' = ''",
]

CUSTOM_POLICY_WHITESPACE_INVALID = [
    "",
    "   ",
    "\n\t",
]


@pytest.mark.security
@pytest.mark.parametrize("expression", CUSTOM_POLICY_DML_BLOCKED)
def test_custom_policy_blocks_dml_keywords_without_semicolon(expression):
    with pytest.raises(PolicyError, match="forbidden SQL tokens"):
        CustomPolicy("dml_blocked", expression=expression)


@pytest.mark.security
@pytest.mark.parametrize("expression", CUSTOM_POLICY_KNOWN_LIMITATIONS)
def test_custom_policy_known_limitation_expressions_allowed(expression):
    """Quote-break / tautology patterns are developer-supplied — prefer ModelPolicy."""
    policy = CustomPolicy("known_limitation", expression=expression)
    assert policy.get_sql_expression() == expression


@pytest.mark.security
@pytest.mark.parametrize("expression", CUSTOM_POLICY_WHITESPACE_INVALID)
def test_custom_policy_rejects_blank_expression(expression):
    with pytest.raises(PolicyError, match="expression is required"):
        CustomPolicy("blank", expression=expression)


@pytest.mark.security
def test_custom_policy_expression_embedded_verbatim_in_ddl():
    expression = "is_public = true AND archived = false"
    editor = RLSDatabaseSchemaEditor(Mock())
    editor.execute = Mock()
    editor.quote_name = lambda name: f'"{name}"'

    policy = CustomPolicy("public_only", expression=expression)
    model = Mock()
    model._meta.db_table = "tests_document"

    editor.create_policy(model, policy)

    sql = editor.execute.call_args[0][0]
    assert f"USING ({expression})" in sql
    assert f"WITH CHECK ({expression})" in sql


@pytest.mark.security
def test_custom_policy_select_subqueries_remain_allowed():
    expression = (
        "id IN (SELECT document_id FROM tests_userpermission "
        "WHERE user_id = 1 AND can_view = true)"
    )
    policy = CustomPolicy("acl_subquery", expression=expression)
    assert policy.get_sql_expression() == expression


@pytest.mark.security
def test_custom_policy_recursive_cte_union_remain_allowed():
    expression = (
        "department_id IN ("
        "WITH RECURSIVE dept_tree AS ("
        "    SELECT id FROM tests_department WHERE id = 1 "
        "    UNION SELECT d.id FROM tests_department d "
        "    INNER JOIN dept_tree dt ON d.parent_id = dt.id"
        ") SELECT id FROM dept_tree)"
    )
    policy = CustomPolicy("hierarchy", expression=expression)
    assert "UNION SELECT" in policy.get_sql_expression()
