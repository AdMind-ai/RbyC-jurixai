import os
import secrets
from .settings import *
from .settings import BASE_DIR

ALLOWED_HOSTS = ['.azurecontainerapps.io', 'localhost']
CSRF_TRUSTED_ORIGINS = ['https://*.azurecontainerapps.io']

# List of allowed origins for CORS (Cross-Origin Resource Sharing)
# CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "https://brave-sand-009d90510.6.azurestaticapps.net",
]
CORS_ALLOW_CREDENTIALS = True


# Disable debug mode in production
DEBUG = False
DEBUG_PROPAGATE_EXCEPTIONS = True
SECRET_KEY = os.getenv('AZURE_SECRET_KEY') or secrets.token_hex()

# Middleware configuration for handling requests and security
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # Basic middleware for common operations
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # Handle user authentication
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Handle Django messages framework
    'django.contrib.messages.middleware.MessageMiddleware',
    # Protect against clickjacking
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SESSION_ENGINE = 'django.contrib.sessions.backends.db'


# Descomentar quando tiver DB setado
# # Retrieve database connection string from environment variables
# CONNECTION = os.environ['AZURE_POSTGRESQL_CONNECTIONSTRING']
# # Convert connection string into a dictionary
# CONNECTION_STR = {pair.split('=')[0]: pair.split('=')[1]
#                   for pair in CONNECTION.split(' ')}

# # Database configuration for PostgreSQL
# DATABASES = {
#     "default": {
#         # Use PostgreSQL as the database backend
#         "ENGINE": "django.db.backends.postgresql",
#         # Database name from connection string
#         "NAME": CONNECTION_STR['dbname'],
#         "HOST": CONNECTION_STR['host'],  # Database host from connection string
#         "USER": CONNECTION_STR['user'],  # Database user from connection string
#         # Database password from connection string
#         "PASSWORD": CONNECTION_STR['password'],
#     }
# }


STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
}
