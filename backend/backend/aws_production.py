import os

from .settings import *


def _split_env(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


DEBUG = False
DEBUG_PROPAGATE_EXCEPTIONS = True
SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = _split_env('DJANGO_ALLOWED_HOSTS') or ['localhost']
CSRF_TRUSTED_ORIGINS = _split_env('DJANGO_CSRF_TRUSTED_ORIGINS')
CORS_ALLOWED_ORIGINS = _split_env('DJANGO_CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ['DB_NAME'],
        "HOST": os.environ['DB_HOST'],
        "PORT": os.environ.get('DB_PORT', '5432'),
        "USER": os.environ['DB_USER'],
        "PASSWORD": os.environ['DB_PASSWORD'],
    }
}

STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
}
