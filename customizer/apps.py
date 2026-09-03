from django.apps import AppConfig
import os


class CustomizerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'customizer'

    def ready(self):
        # Additional safety check for serverless environments
        pass
