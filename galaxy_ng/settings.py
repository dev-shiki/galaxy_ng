# Minimal test settings for Galaxy NG

# Use in-memory SQLite for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Make sure the secret key is consistent
SECRET_KEY = 'test-key-for-galaxy-ng-testing'

# Explicitly enable timezone to avoid warnings
USE_TZ = True

# Disable CSRF for testing
MIDDLEWARE = []

# Minimal installed apps
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
]

# Simplified auth for testing
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
