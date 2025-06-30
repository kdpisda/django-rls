from django.apps import AppConfig


class DjangoRLSConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_rls"
    verbose_name = "Django RLS"

    def ready(self):
        """Initialize RLS when Django starts."""
        from . import signals  # noqa