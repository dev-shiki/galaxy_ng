from pulpcore.app.settings import *
# Test-specific settings
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
