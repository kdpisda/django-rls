"""
Regression tests for Issue #72.

``ModelPolicy(operation=SELECT)`` (and DELETE) emitted an invalid
``WITH CHECK`` clause alongside ``USING``, which PostgreSQL rejects with
"WITH CHECK cannot be applied to SELECT or DELETE". The root cause was that
``RLSDatabaseSchemaEditor.create_policy``/``alter_policy`` called
``policy.get_compiled_sql(model)`` unconditionally for both clauses whenever
a policy exposed model-aware compilation (``ModelPolicy``), ignoring
``policy.operation`` entirely.

PostgreSQL's rules, per ``CREATE POLICY``:
  * SELECT / DELETE -> USING only
  * INSERT           -> WITH CHECK only
  * UPDATE / ALL     -> both USING and WITH CHECK
"""

from unittest.mock import Mock, patch

import pytest
from django.db import connection, models
from django.db.models import Q
from django.test import TestCase

from django_rls.backends.postgresql.base import RLSDatabaseSchemaEditor
from django_rls.models import RLSModel
from django_rls.policies import BasePolicy, ModelPolicy, UserPolicy

# operation -> (expect USING clause, expect WITH CHECK clause)
OPERATION_EXPECTATIONS = [
    (BasePolicy.SELECT, True, False),
    (BasePolicy.DELETE, True, False),
    (BasePolicy.INSERT, False, True),
    (BasePolicy.UPDATE, True, True),
    (BasePolicy.ALL, True, True),
]


class _CountryModel(RLSModel):
    """Real model needed by ModelPolicy.get_compiled_sql(), which compiles
    an actual Django ``Query`` against the model's ``_meta`` (a Mock won't
    do)."""

    country = models.CharField(max_length=8)

    class Meta:
        app_label = "tests"
        rls_policies = []


class TestSchemaEditorClauseGatingForModelPolicy(TestCase):
    """Unit-level coverage of the exact code path the issue reports.

    ``ModelPolicy`` is the policy type that routes through
    ``get_compiled_sql`` in the schema editor, which is where the clauses
    were previously generated unconditionally.
    """

    def setUp(self):
        self.editor = RLSDatabaseSchemaEditor(Mock())
        self.editor.execute = Mock()
        self.editor.quote_name = lambda x: f'"{x}"'
        self.model = _CountryModel

    def test_operations_produce_only_valid_clauses(self):
        for operation, wants_using, wants_check in OPERATION_EXPECTATIONS:
            with self.subTest(operation=operation):
                policy = ModelPolicy(
                    f"policy_{operation.lower()}",
                    filters=Q(country="US"),
                    operation=operation,
                )
                self.editor.execute.reset_mock()
                self.editor.create_policy(self.model, policy)

                sql = self.editor.execute.call_args[0][0]
                assert (f"FOR {operation}" in sql), sql
                assert ("USING (" in sql) is wants_using, sql
                assert ("WITH CHECK (" in sql) is wants_check, sql

    def test_alter_policy_also_gates_clauses(self):
        policy = ModelPolicy(
            "select_policy", filters=Q(country="US"), operation=BasePolicy.SELECT
        )
        self.editor.alter_policy(self.model, policy)

        sql = self.editor.execute.call_args[0][0]
        assert "USING (" in sql
        assert "WITH CHECK (" not in sql

    def test_compiles_sql_only_once_when_both_clauses_are_needed(self):
        """Compiling a Q object (filter rewriting + running the SQL
        compiler) is expensive; UPDATE/ALL policies need both USING and
        WITH CHECK but must only pay for compilation once."""
        for operation in (BasePolicy.UPDATE, BasePolicy.ALL):
            with self.subTest(operation=operation):
                policy = ModelPolicy(
                    f"policy_{operation.lower()}",
                    filters=Q(country="US"),
                    operation=operation,
                )
                with patch.object(
                    ModelPolicy, "get_compiled_sql", wraps=policy.get_compiled_sql
                ) as spy:
                    self.editor.execute.reset_mock()
                    self.editor.create_policy(self.model, policy)

                assert spy.call_count == 1
                sql = self.editor.execute.call_args[0][0]
                assert "USING (" in sql
                assert "WITH CHECK (" in sql


class TestSchemaEditorClauseGatingForExpressionPolicy(TestCase):
    """Same coverage for the get_using_expression/get_check_expression path
    (e.g. UserPolicy, TenantPolicy, CustomPolicy)."""

    def setUp(self):
        self.editor = RLSDatabaseSchemaEditor(Mock())
        self.editor.execute = Mock()
        self.editor.quote_name = lambda x: f'"{x}"'
        self.model = Mock()
        self.model._meta.db_table = "test_table"

    def test_operations_produce_only_valid_clauses(self):
        for operation, wants_using, wants_check in OPERATION_EXPECTATIONS:
            with self.subTest(operation=operation):
                policy = UserPolicy(
                    f"user_policy_{operation.lower()}",
                    user_field="owner",
                    operation=operation,
                )
                self.editor.execute.reset_mock()
                self.editor.create_policy(self.model, policy)

                sql = self.editor.execute.call_args[0][0]
                assert ("USING (" in sql) is wants_using, sql
                assert ("WITH CHECK (" in sql) is wants_check, sql


class TestBasePolicyExpressionGating:
    """BasePolicy.get_using_expression/get_check_expression should also be
    gated on operation, independent of the schema editor."""

    def test_get_using_expression_omitted_for_insert(self):
        policy = UserPolicy("p", user_field="owner", operation=BasePolicy.INSERT)
        assert policy.get_using_expression() is None
        assert policy.get_check_expression() is not None

    def test_get_check_expression_omitted_for_select(self):
        policy = UserPolicy("p", user_field="owner", operation=BasePolicy.SELECT)
        assert policy.get_using_expression() is not None
        assert policy.get_check_expression() is None

    def test_get_check_expression_omitted_for_delete(self):
        policy = UserPolicy("p", user_field="owner", operation=BasePolicy.DELETE)
        assert policy.get_using_expression() is not None
        assert policy.get_check_expression() is None

    def test_both_present_for_update_and_all(self):
        for operation in (BasePolicy.UPDATE, BasePolicy.ALL):
            policy = UserPolicy("p", user_field="owner", operation=operation)
            assert policy.get_using_expression() is not None
            assert policy.get_check_expression() is not None


@pytest.mark.django_db(transaction=True)
def test_model_policy_ddl_is_accepted_by_postgres_for_every_operation():
    """
    End-to-end reproduction of the issue's repro case: creating RLS policies
    for every operation must not raise
    ``ProgrammingError: WITH CHECK cannot be applied to SELECT or DELETE``,
    and PostgreSQL's own catalog must reflect only the applicable clauses.
    """
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL")

    class Document(RLSModel):
        country = models.CharField(max_length=8)

        class Meta:
            app_label = "tests"
            db_table = "issue72_document"
            rls_policies = [
                ModelPolicy(
                    "select_by_country", filters=Q(country="US"), operation=BasePolicy.SELECT
                ),
                ModelPolicy(
                    "delete_by_country", filters=Q(country="US"), operation=BasePolicy.DELETE
                ),
                ModelPolicy(
                    "insert_by_country", filters=Q(country="US"), operation=BasePolicy.INSERT
                ),
                ModelPolicy(
                    "update_by_country", filters=Q(country="US"), operation=BasePolicy.UPDATE
                ),
                ModelPolicy(
                    "all_by_country", filters=Q(country="US"), operation=BasePolicy.ALL
                ),
            ]

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(Document)

    try:
        # Prior to the fix this raised:
        # django.db.utils.ProgrammingError: WITH CHECK cannot be applied
        # to SELECT or DELETE
        Document.enable_rls()

        # polcmd: 'r' = SELECT, 'a' = INSERT, 'w' = UPDATE, 'd' = DELETE,
        # '*' = ALL. See https://www.postgresql.org/docs/current/catalog-pg-policy.html
        expected = {
            "select_by_country": ("r", True, False),
            "delete_by_country": ("d", True, False),
            "insert_by_country": ("a", False, True),
            "update_by_country": ("w", True, True),
            "all_by_country": ("*", True, True),
        }

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT polname, polcmd, polqual IS NOT NULL, "
                "polwithcheck IS NOT NULL FROM pg_policy "
                "WHERE polname = ANY(%s)",
                [list(expected)],
            )
            rows = {row[0]: (row[1], row[2], row[3]) for row in cursor.fetchall()}

        assert set(rows) == set(expected)
        for name, expectation in expected.items():
            assert rows[name] == expectation, name

    finally:
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(Document)
