"""
Security Test: Transaction Scope and Autocommit

``set_config`` must use session scope (``is_local=False``) so context survives
autocommit statement boundaries.
"""

import pytest

from django_rls.context import set_rls_context
from django_rls.db.functions import get_rls_context


@pytest.mark.security
@pytest.mark.django_db
def test_set_context_uses_session_scope_by_default(require_postgresql):
    set_rls_context("user_id", "123", system=True)

    # Session-scoped settings survive the implicit transaction boundary between
    # separate cursor executes under autocommit. Transaction-local settings do not.
    assert get_rls_context("user_id") == "123"