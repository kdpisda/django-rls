"""
Legacy SQL injection tests — kept for backward compatibility.

See also:
- test_policy_sql_injection.py
- test_context_sql_injection.py
"""

import pytest

from django_rls.exceptions import PolicyError
from django_rls.expressions import RLSExpression
from django_rls.policies import CustomPolicy, TenantPolicy


@pytest.mark.security
def test_rls_expression_escapes_drop_table_payload():
    malicious_value = "1'; DROP TABLE users; --"
    result = RLSExpression("dummy")._format_value(malicious_value)

    assert result != f"'{malicious_value}'"
    assert result == f"'{malicious_value.replace(chr(39), chr(39) * 2)}'"


@pytest.mark.security
@pytest.mark.parametrize(
    "field_name",
    [
        "owner'; DROP TABLE users; --",
        "tenant_id; DELETE FROM secrets",
        "bad-field",
    ],
)
def test_policy_field_injection_rejected(field_name):
    with pytest.raises(PolicyError, match="Invalid field name"):
        TenantPolicy("field_policy", tenant_field=field_name)


@pytest.mark.security
def test_custom_policy_drop_table_blocked():
    with pytest.raises(PolicyError, match="forbidden SQL tokens"):
        CustomPolicy(
            "evil",
            expression="is_public = true; DROP TABLE users; --",
        )
