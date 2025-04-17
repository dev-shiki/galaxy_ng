import os
import sys
import re
import pytest
from unittest import mock

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")
# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

# Use pytest marks for Django database handling
pytestmark = pytest.mark.django_db

