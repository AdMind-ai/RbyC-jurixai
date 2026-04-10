import os


def get_settings_module() -> str:
    explicit_settings = os.getenv("DJANGO_SETTINGS_MODULE")
    if explicit_settings:
        return explicit_settings

    if 'RUNNING_IN_PRODUCTION' in os.environ:
        return 'backend.azure_production'
    if 'WEBSITE_HOSTNAME' in os.environ:
        return 'backend.production'
    return 'backend.settings'
