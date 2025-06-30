"""Management command to enable RLS for all RLS models."""

from django.core.management.base import BaseCommand
from django.apps import apps

from django_rls.models import RLSModel


class Command(BaseCommand):
    help = "Enable RLS for all RLS models"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Enable RLS only for models in specified app',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Enable RLS only for specified model',
        )
    
    def handle(self, *args, **options):
        app_label = options.get('app')
        model_name = options.get('model')
        
        models = self._get_rls_models(app_label, model_name)
        
        for model in models:
            try:
                model.enable_rls()
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully enabled RLS for {model._meta.label}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to enable RLS for {model._meta.label}: {e}')
                )
    
    def _get_rls_models(self, app_label=None, model_name=None):
        """Get all RLS models."""
        models = []
        
        for model in apps.get_models():
            if issubclass(model, RLSModel) and hasattr(model, '_rls_policies'):
                if app_label and model._meta.app_label != app_label:
                    continue
                if model_name and model._meta.model_name != model_name.lower():
                    continue
                models.append(model)
        
        return models