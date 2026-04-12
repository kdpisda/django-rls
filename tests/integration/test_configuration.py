from unittest.mock import MagicMock

import pytest
from django.core.management import call_command
from django.test import override_settings


@override_settings(DJANGO_RLS={"AUTO_ENABLE_RLS": True})
@pytest.mark.django_db
def test_enable_rls_enabled_on_migrate():
    from django_rls.models import RLSModel

    original_enable_rls = RLSModel.enable_rls
    enable_rls = MagicMock()
    RLSModel.enable_rls = enable_rls

    call_command("migrate")

    enable_rls.assert_called()

    RLSModel.enable_rls = original_enable_rls


@override_settings(DJANGO_RLS={"AUTO_ENABLE_RLS": False})
@pytest.mark.django_db
def test_enable_rls_disabled_on_migrate():
    from django_rls.models import RLSModel

    original_enable_rls = RLSModel.enable_rls
    enable_rls = MagicMock()
    RLSModel.enable_rls = enable_rls

    call_command("migrate")

    enable_rls.assert_not_called()

    RLSModel.enable_rls = original_enable_rls
