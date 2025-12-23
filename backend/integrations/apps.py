from django.apps import AppConfig

class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "integrations"
    verbose_name = "Integrations"
    
    def ready(self):
        # Import the drf-spectacular extensions so custom auth is discovered
        # by the schema generator. Import inside ready() to avoid import
        # side-effects at module import time.
        try:
            import integrations.spectacular  # noqa: F401
        except Exception:
            # Be defensive: failure to import the extension shouldn't
            # prevent the app from starting.
            pass