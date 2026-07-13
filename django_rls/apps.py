from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver


class DjangoRLSConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_rls"
    verbose_name = "Django RLS"

    def ready(self):
        """Initialize RLS when Django starts."""
        import django_rls.signals  # noqa: F401
        from django_rls.conf import rls_config

        if rls_config.reset_context_on_connect:
            connection_created.connect(
                _reset_rls_on_connection, dispatch_uid="django_rls_reset_context"
            )


def _reset_rls_on_connection(sender, connection, **kwargs):
    if connection.vendor != "postgresql":
        return
    from django_rls.context import reset_connection_rls_context

    reset_connection_rls_context()
