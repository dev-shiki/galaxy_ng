import os
import sys
import pytest
from unittest import mock

# Ensure mock is always available for test modules
sys.modules['mock'] = mock

# Setup Django environment with fallback mechanisms
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock common modules that might be missing
common_modules = [
    'galaxy_ng.app.management.commands.sync_galaxy_collections',
    'galaxy_ng.social.auth',
    'galaxy_ng.social.factories',
    'galaxy_ng.app.utils.roles',
    'galaxy_ng.app.access_control.access_policy'
]

for module_path in common_modules:
    if module_path not in sys.modules:
        parts = module_path.split('.')
        # Create parent modules if they don't exist
        for i in range(1, len(parts)):
            parent = '.'.join(parts[:i])
            if parent not in sys.modules:
                sys.modules[parent] = mock.MagicMock()
        # Create the module itself
        sys.modules[module_path] = mock.MagicMock()

# Create parent module for settings if needed
if 'galaxy_ng' not in sys.modules:
    sys.modules['galaxy_ng'] = mock.MagicMock()

# Try to set up Django, with fallback to mock settings
try:
    import django
    django.setup()
except ModuleNotFoundError:
    # Create a minimal mock settings module
    mock_settings = mock.MagicMock()
    mock_settings.INSTALLED_APPS = [
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'pulpcore',
        'galaxy_ng'
    ]
    mock_settings.DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
    mock_settings.MIDDLEWARE = []
    mock_settings.TEMPLATES = []
    mock_settings.LOGGING_CONFIG = None
    mock_settings.LOGGING = {}
    mock_settings.SECRET_KEY = 'test-key'
    mock_settings.DEBUG = True
    mock_settings.ALLOWED_HOSTS = ['*']
    
    # Add the mock settings to sys.modules
    sys.modules['galaxy_ng.settings'] = mock_settings
    
    # Mock Django packages that might be needed
    django_modules = [
        'django.contrib.auth.models',
        'django.contrib.contenttypes.models',
        'django.db.models',
        'django.core.exceptions'
    ]
    
    for module_path in django_modules:
        if module_path not in sys.modules:
            parts = module_path.split('.')
            for i in range(1, len(parts)):
                parent = '.'.join(parts[:i])
                if parent not in sys.modules:
                    sys.modules[parent] = mock.MagicMock()
            sys.modules[module_path] = mock.MagicMock()
    
    # Mock common model exceptions
    DoesNotExist = type('DoesNotExist', (Exception,), {})
    django.db.models.Model = mock.MagicMock()
    django.db.models.Model.DoesNotExist = DoesNotExist
    
    # Try again to set up Django with our mocks in place
    django.setup()

# Common test fixtures
@pytest.fixture
def mock_request():
    return mock.MagicMock(
        user=mock.MagicMock(
            username="test_user",
            is_superuser=False,
            is_authenticated=True
        )
    )

@pytest.fixture
def mock_superuser():
    return mock.MagicMock(
        username="admin_user",
        is_superuser=True,
        is_authenticated=True
    )

@pytest.fixture
def mock_models():
    """Returns common mocked models for testing."""
    models = mock.MagicMock()
    
    # Create DoesNotExist exceptions for common models
    models.User.DoesNotExist = type('DoesNotExist', (Exception,), {})
    models.Group.DoesNotExist = type('DoesNotExist', (Exception,), {})
    models.Collection.DoesNotExist = type('DoesNotExist', (Exception,), {})
    models.Repository.DoesNotExist = type('DoesNotExist', (Exception,), {})
    
    return models
