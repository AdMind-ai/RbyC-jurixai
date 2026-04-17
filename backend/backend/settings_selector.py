import os


def get_settings_module() -> str:
    explicit_settings = os.getenv("DJANGO_SETTINGS_MODULE")
    if explicit_settings:
        return explicit_settings

    return 'backend.settings'
