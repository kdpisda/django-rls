"""
Integration Test: Context Processors & Email Bypass

Verifies that users can inject arbitrary context (e.g., email) via middleware
and use it in policies to grant bypass access.
"""
import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.db import connection, models
from django.db.models import CharField, Q
from django.test import RequestFactory, TransactionTestCase

from django_rls.db.functions import get_rls_context
from django_rls.middleware import RLSContextMiddleware
from django_rls.models import RLSModel
from django_rls.policies import RLS, ModelPolicy


# Mock Processor
def email_context_processor(request):
    if hasattr(request, "user") and not isinstance(request.user, AnonymousUser):
        return {"user_email": request.user.email}
    return {}


@pytest.mark.django_db(transaction=True)
class TestContextProcessors(TransactionTestCase):
    def setUp(self):
        if connection.vendor != "postgresql":
            pytest.skip("Skipping RLS tests: Database is not PostgreSQL")

        self.factory = RequestFactory()

        # Create Users
        self.u_admin = User.objects.create_user("admin", email="boss@platform.com")
        self.u_user = User.objects.create_user("user", email="user@other.com")
        self.u_hacker = User.objects.create_user(
            "hacker", email="fake@platform.com.evil"
        )

    def test_email_bypass_policy(self):
        """
        Verify policy: Allow IF email ends with '@platform.com' OR owner.
        """

        class PlatformAsset(RLSModel):
            secret_data = models.CharField(max_length=100)
            owner = models.ForeignKey(User, on_delete=models.CASCADE)

            class Meta:
                app_label = "tests"
                db_table = "platform_asset"
                rls_policies = [
                    ModelPolicy(
                        "platform_access",
                        filters=Q(ctx_email__endswith="@platform.com")
                        | Q(owner=RLS.user_id()),
                        annotations={
                            # Map lookup alias to SQL Expression
                            "ctx_email": RLS.context(
                                "user_email", output_field=CharField()
                            )
                        },
                    )
                ]

        # 1. Create Model
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(PlatformAsset)

        try:
            # Create Data (Before RLS)
            asset = PlatformAsset.objects.create(
                secret_data="Blueprints", owner=self.u_user
            )

            PlatformAsset.enable_rls()
            with connection.cursor() as cursor:
                cursor.execute(
                    f"ALTER TABLE {PlatformAsset._meta.db_table} FORCE ROW LEVEL "
                    f"SECURITY"
                )

            # 2. Test Middleware & Access

            # Setup Middleware with Mock Processor
            # We patch settings to include our processor
            # Note: We can't easily patch string import without it being importable.
            # But we can monkeypatch the middleware's logic or ensure the processor is
            # importable.
            # For test simplicity, we will Mock the import_string logic OR just
            # subclass middleware?
            # Let's manual-drive the middleware logic to ensure set_rls_context works.

            # Actually, let's verify the Middleware *calls* the processor.
            # We will use 'override_settings' with a string path if possible?
            # "django_rls.simple_context.simple_email_processor"

            proc_path = "django_rls.simple_context.simple_email_processor"

            proc_path = "django_rls.simple_context.simple_email_processor"

            # Helper to create a middleware that runs our check
            def create_checking_mw(check_fn):
                return RLSContextMiddleware(lambda r: check_fn(r))

            with self.settings(RLS_CONTEXT_PROCESSORS=[proc_path]):
                # A. Test Admin (Platform Email)
                req_admin = self.factory.get("/")
                req_admin.session = {}
                req_admin.user = self.u_admin

                def check_admin(r):
                    # Verify Context is set locally
                    assert get_rls_context("user_email") == "boss@platform.com"
                    # Verify Visibility
                    return PlatformAsset.objects.filter(pk=asset.pk).exists()

                mw_admin = create_checking_mw(check_admin)
                is_visible = mw_admin(req_admin)
                self.assertTrue(
                    is_visible, "Admin with platform email should see asset"
                )

                # Verify Context Cleared
                self.assertIsNone(get_rls_context("user_email"))

                # B. Test User (Other Email)
                req_user = self.factory.get("/")
                req_user.session = {}
                req_user.user = self.u_user

                def check_user(r):
                    assert get_rls_context("user_email") == "user@other.com"
                    # User IS owner
                    return PlatformAsset.objects.filter(pk=asset.pk).exists()

                mw_user = create_checking_mw(check_user)
                is_visible = mw_user(req_user)
                self.assertTrue(is_visible, "Owner should see asset")

                # C. Test Hacker (Bad Email)
                req_hacker = self.factory.get("/")
                req_hacker.session = {}
                req_hacker.user = self.u_hacker

                def check_hacker(r):
                    # NOT owner, Email ends with .evil
                    return PlatformAsset.objects.filter(pk=asset.pk).exists()

                mw_hacker = create_checking_mw(check_hacker)
                is_visible = mw_hacker(req_hacker)
                self.assertFalse(is_visible, "Hacker should NOT see asset")

        finally:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(PlatformAsset)
