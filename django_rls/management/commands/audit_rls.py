"""Management command to audit RLS configuration for production readiness."""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection

from django_rls.models import RLSModel
from django_rls.policies import CustomPolicy


class Command(BaseCommand):
    help = (
        "Audit Row Level Security configuration: FORCE RLS, enabled tables, "
        "and models using CustomPolicy."
    )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stderr.write(
                self.style.ERROR("audit_rls requires a PostgreSQL database.")
            )
            return

        issues = []
        warnings = []

        custom_policy_models = []
        rls_models = []

        for model in apps.get_models():
            if not issubclass(model, RLSModel) or model._meta.abstract:
                continue
            if not getattr(model, "_rls_policies", None):
                continue
            rls_models.append(model)
            for policy in model._rls_policies:
                if isinstance(policy, CustomPolicy):
                    custom_policy_models.append(model._meta.label)

        self.stdout.write(self.style.MIGRATE_HEADING("RLS audit report"))
        self.stdout.write(f"RLS models found: {len(rls_models)}")

        with connection.cursor() as cursor:
            for model in rls_models:
                table = model._meta.db_table
                cursor.execute(
                    """
                    SELECT c.relrowsecurity, c.relforcerowsecurity
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = %s AND n.nspname = current_schema()
                    """,
                    [table],
                )
                row = cursor.fetchone()
                if not row:
                    issues.append(f"{model._meta.label}: table {table!r} not found")
                    continue

                rls_enabled, force_rls = row
                if not rls_enabled:
                    issues.append(f"{model._meta.label}: RLS not enabled on {table}")
                elif not force_rls:
                    issues.append(
                        f"{model._meta.label}: FORCE ROW LEVEL SECURITY not set "
                        f"on {table} (table owner can bypass policies)"
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  OK  {model._meta.label} ({table}): RLS + FORCE"
                        )
                    )

                cursor.execute(
                    """
                    SELECT policyname, permissive, roles, cmd
                    FROM pg_policies
                    WHERE schemaname = current_schema() AND tablename = %s
                    """,
                    [table],
                )
                policies = cursor.fetchall()
                if not policies:
                    warnings.append(
                        f"{model._meta.label}: RLS enabled but no policies on {table}"
                    )
                for pname, permissive, roles, cmd in policies:
                    self.stdout.write(
                        f"       policy {pname!r}: cmd={cmd}, roles={roles}, "
                        f"permissive={permissive}"
                    )

        if custom_policy_models:
            warnings.append(
                "Models using CustomPolicy (prefer ModelPolicy): "
                + ", ".join(sorted(set(custom_policy_models)))
            )

        if warnings:
            self.stdout.write(self.style.WARNING("\nWarnings:"))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f"  - {warning}"))

        if issues:
            self.stdout.write(self.style.ERROR("\nIssues (must fix for production):"))
            for issue in issues:
                self.stdout.write(self.style.ERROR(f"  - {issue}"))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("\nRLS audit passed."))
