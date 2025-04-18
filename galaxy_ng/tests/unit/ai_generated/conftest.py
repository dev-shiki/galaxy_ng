import os
import sys
import pytest

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Django and setup
import django
django.setup()

# Add fixtures here if needed
@pytest.fixture
def mock_request():
    from unittest.mock import MagicMock
    return MagicMock()
