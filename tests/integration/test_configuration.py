from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test import override_settings


@override_settings(DJANGO_RLS={"AUTO_ENABLE_RLS": True})
@pytest.mark.django_db
def test_enable_rls_enabled_on_migrate():
    from django_rls.models import RLSModel

    with patch.object(RLSModel, "enable_rls") as enable_rls:
        call_command("migrate")
        enable_rls.assert_called()


@override_settings(DJANGO_RLS={"AUTO_ENABLE_RLS": False})
@pytest.mark.django_db
def test_enable_rls_disabled_on_migrate():
    from django_rls.models import RLSModel

    with patch.object(RLSModel, "enable_rls") as enable_rls:
        call_command("migrate")
        enable_rls.assert_not_called()
