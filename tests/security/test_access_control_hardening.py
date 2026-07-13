"""
Regression tests: access-control hardening (non-SQL).

Covers identity immutability, middleware trust boundaries, and tenant session policy.
"""

from unittest.mock import Mock

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, override_settings

from django_rls.context import (
    get_active_rls_context,
    rls_context,
    set_rls_context,
    system_rls_context,
)
from django_rls.db.functions import get_rls_context
from django_rls.exceptions import (
    RLSContextImmutableError,
    RLSContextRequiredError,
    TenantAccessDeniedError,
)
from django_rls.middleware import RLSContextMiddleware


def deny_all_tenants(request, tenant_id):
    return False


@pytest.fixture(autouse=True)
def _reset_context():
    from django_rls.context import _active_context, _context_source, _identity_locked

    _active_context.set({})
    _identity_locked.set(False)
    _context_source.set(None)
    yield
    _active_context.set({})
    _identity_locked.set(False)
    _context_source.set(None)


@pytest.mark.security
@pytest.mark.django_db
def test_user_id_cannot_be_overridden_without_system_mode(require_postgresql):
    set_rls_context("user_id", 1, system=True)
    with pytest.raises(RLSContextImmutableError, match="Cannot override protected"):
        set_rls_context("user_id", 2)


@pytest.mark.security
@pytest.mark.django_db
def test_tenant_id_cannot_be_overridden_without_system_mode(require_postgresql):
    set_rls_context("tenant_id", 10, system=True)
    with pytest.raises(RLSContextImmutableError):
        set_rls_context("tenant_id", 20)


@pytest.mark.security
@pytest.mark.django_db
def test_custom_context_keys_remain_mutable(require_postgresql):
    set_rls_context("user_id", 1, system=True)
    set_rls_context("department_id", "sales")
    set_rls_context("department_id", "engineering")
    assert get_active_rls_context()["department_id"] == "engineering"
    assert get_rls_context("department_id") == "engineering"


@pytest.mark.security
@pytest.mark.django_db
def test_system_rls_context_allows_privileged_switch(require_postgresql):
    set_rls_context("user_id", 1, system=True)
    with system_rls_context(user_id=99):
        assert get_active_rls_context()["user_id"] == "99"
        assert get_rls_context("user_id") == "99"


@pytest.mark.security
@pytest.mark.django_db
def test_rls_context_manager_blocks_nested_identity_override(require_postgresql):
    with rls_context(system=True, user_id=10):
        with pytest.raises(RLSContextImmutableError):
            with rls_context(user_id=20):
                pass


@pytest.mark.security
@pytest.mark.django_db
def test_headers_cannot_inject_user_context(require_postgresql):
    factory = RequestFactory()
    middleware = RLSContextMiddleware(lambda request: Mock())
    request = factory.get("/")
    request.user = Mock(id=123, spec=[])
    request.session = {}
    request.META["HTTP_X_RLS_USER_ID"] = "999"
    request.GET = {"rls_user_id": "777"}

    middleware._set_rls_context(request)

    assert get_active_rls_context() == {"user_id": "123"}
    assert get_rls_context("user_id") == "123"


@pytest.mark.security
@pytest.mark.django_db
def test_json_body_cannot_inject_user_context(require_postgresql):
    factory = RequestFactory()
    middleware = RLSContextMiddleware(lambda request: Mock())
    request = factory.post(
        "/",
        data='{"user_id": 999, "tenant_id": "1; DROP TABLE x"}',
        content_type="application/json",
    )
    request.user = Mock(id=123, spec=[])

    middleware._set_rls_context(request)

    assert get_active_rls_context() == {"user_id": "123"}
    assert get_rls_context("user_id") == "123"


@pytest.mark.security
@pytest.mark.django_db
def test_session_tenant_ignored_by_default(require_postgresql):
    factory = RequestFactory()
    middleware = RLSContextMiddleware(lambda request: Mock())
    request = factory.get("/")
    request.user = AnonymousUser()
    request.session = {"tenant_id": 42}

    middleware._set_rls_context(request)

    assert get_active_rls_context() == {}
    assert get_rls_context("tenant_id") in (None, "")


@pytest.mark.security
@pytest.mark.django_db
@override_settings(DJANGO_RLS={"ALLOW_SESSION_TENANT": True})
def test_session_tenant_allowed_only_when_opted_in(require_postgresql):
    factory = RequestFactory()
    middleware = RLSContextMiddleware(lambda request: Mock())
    request = factory.get("/")
    request.user = AnonymousUser()
    request.session = {"tenant_id": 42}

    middleware._set_rls_context(request)

    assert get_active_rls_context() == {"tenant_id": "42"}
    assert get_rls_context("tenant_id") == "42"


@pytest.mark.security
@override_settings(
    DJANGO_RLS={
        "TENANT_MEMBERSHIP_VALIDATOR": (
            "tests.security.test_access_control_hardening.deny_all_tenants"
        )
    }
)
def test_tenant_membership_validator_can_deny():
    factory = RequestFactory()
    middleware = RLSContextMiddleware(lambda request: Mock())
    request = factory.get("/")
    request.user = Mock(id=1, spec=[])
    request.tenant = Mock(id=99)
    request.session = {}

    with pytest.raises(TenantAccessDeniedError):
        middleware._set_rls_context(request)


@pytest.mark.security
@override_settings(DJANGO_RLS={"REQUIRE_CONTEXT": True})
def test_require_context_raises_when_identity_missing():
    from django_rls.context import require_rls_context

    with pytest.raises(RLSContextRequiredError, match="identity context is required"):
        require_rls_context()


@pytest.mark.security
@pytest.mark.django_db
@override_settings(DJANGO_RLS={"REQUIRE_CONTEXT": True})
def test_require_context_passes_when_user_id_set(require_postgresql):
    from django_rls.context import require_rls_context

    set_rls_context("user_id", 5, system=True)
    require_rls_context()