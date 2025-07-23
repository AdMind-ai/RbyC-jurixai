import os
from .settings import *  # Import all settings from the base settings file
from .settings import BASE_DIR  # Import BASE_DIR from the base settings file

# Allowed domains the project is allowed to serve
website_hostname = os.getenv('WEBSITE_HOSTNAME')
print("HOST: ", website_hostname)

ALLOWED_HOSTS = [os.environ['WEBSITE_HOSTNAME']]

# List of trusted origins for unsafe requests (e.g., CSRF protection)
CSRF_TRUSTED_ORIGINS = ['https://' + os.environ['WEBSITE_HOSTNAME']]

# List of allowed origins for CORS (Cross-Origin Resource Sharing)
# CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://app.investorai.it",
]


# Disable debug mode in production
DEBUG = False
SECRET_KEY = os.environ['SECRET_KEY']

# Middleware configuration for handling requests and security
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Handle CORS requests
    'django.middleware.security.SecurityMiddleware',  # Basic security middleware
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files efficiently
    'django.contrib.sessions.middleware.SessionMiddleware',  # Handle user sessions
    # Basic middleware for common operations
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # Protect against CSRF attacks
    # Handle user authentication
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Handle Django messages framework
    'django.contrib.messages.middleware.MessageMiddleware',
    # Protect against clickjacking
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# Retrieve database connection string from environment variables
CONNECTION = os.environ['AZURE_POSTGRESQL_CONNECTIONSTRING']
# Convert connection string into a dictionary
CONNECTION_STR = {pair.split('=')[0]: pair.split('=')[1]
                  for pair in CONNECTION.split(' ')}

# Database configuration for PostgreSQL
DATABASES = {
    "default": {
        # Use PostgreSQL as the database backend
        "ENGINE": "django.db.backends.postgresql",
        # Database name from connection string
        "NAME": CONNECTION_STR['dbname'],
        "HOST": CONNECTION_STR['host'],  # Database host from connection string
        "USER": CONNECTION_STR['user'],  # Database user from connection string
        # Database password from connection string
        "PASSWORD": CONNECTION_STR['password'],
    }
}


STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
}
