import uuid
from unittest.mock import MagicMock

import pytest
from django.db import models
from django.db.models import UUIDField

from django_rls.policies import RLS, CurrentContext, UserContext


def test_user_context_defaults_to_integer():
    """
    Test that UserContext resolves to IntegerField for the default User model.
    """
    from django.db.models import IntegerField

    ctx = UserContext()
    ctx.resolve_expression()
    # Default User model has Integer PK
    assert isinstance(ctx.output_field, IntegerField)


def test_current_context_generates_uuid_cast():
    """
    Test that CurrentContext generates ::uuid cast for UUIDField.
    """

    ctx = CurrentContext(models.Value("rls.user_id"), output_field=UUIDField())

    # Needs to be resolved to get SQL?
    # as_postgresql calls as_sql
    # accessing as_postgresql directly for unit test

    # Only Postgres backend has this method usually if using specialized Lookups,
    # but CurrentContext implements it directly.

    # Mock compiler/connection
    mock_compiler = MagicMock()
    mock_compiler.compile = lambda x: ("%s", [])
    mock_connection = MagicMock()

    sql, params = ctx.as_postgresql(mock_compiler, mock_connection)

    # Expected: "(NULLIF(current_setting(%s, true), ''))::uuid"
    # Note: The template is "NULLIF..."
    # The cast is appended in as_postgresql

    assert "::uuid" in sql
    assert "current_setting" in sql


@pytest.mark.django_db
def test_integration_uuid_field():
    """
    Integration test: Verify we can actually filter a UUID field
    against a session variable using the cast.
    """
    from django.db import connection
    from django.db.models import Q

    from django_rls.db.functions import set_rls_context
    from django_rls.models import RLSModel
    from django_rls.policies import ModelPolicy

    class UUIDDoc(RLSModel):
        id = models.UUIDField(primary_key=True, default=uuid.uuid4)
        # owner_id stored as UUID
        owner_uuid = models.UUIDField()

        class Meta:
            app_label = "tests"
            db_table = "uuid_doc"
            rls_policies = [
                ModelPolicy(
                    "uuid_match",
                    filters=Q(
                        owner_uuid=RLS.context("current_uuid", output_field=UUIDField())
                    ),
                )
            ]

    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(UUIDDoc)

    my_uuid = uuid.uuid4()
    other_uuid = uuid.uuid4()

    # Create Data (Before RLS)
    doc = UUIDDoc.objects.create(owner_uuid=my_uuid)

    try:
        UUIDDoc.enable_rls()
        with connection.cursor() as cursor:
            cursor.execute(
                f"ALTER TABLE {UUIDDoc._meta.db_table} FORCE ROW LEVEL SECURITY"
            )

        # Test Access
        # 1. Set Context
        set_rls_context("current_uuid", str(my_uuid), is_local=False)

        # 2. Query
        assert UUIDDoc.objects.filter(pk=doc.pk).exists()

        # 3. Wrong Context
        set_rls_context("current_uuid", str(other_uuid), is_local=False)
        assert not UUIDDoc.objects.filter(pk=doc.pk).exists()

    finally:
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(UUIDDoc)
