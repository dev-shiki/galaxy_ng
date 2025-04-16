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

  

  # Try to import the module being tested

  try:

      from galaxy_ng.${module_path//_/.} import *

  except ImportError:

      pass  # Module might be in a different location

import os
import sys
import pytest
from unittest import mock
from galaxy_ng.app.utils.galaxy import (
    generate_unverified_email,
    uuid_to_int,
    int_to_uuid,
    safe_fetch,
    paginated_results,
    find_namespace,
    get_namespace_owners_details,
    upstream_namespace_iterator,
    upstream_collection_iterator,
    upstream_role_iterator,
)
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from galaxy_ng.tests import factories

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def mock_safe_fetch(mocker):
    return mocker.patch('galaxy_ng.app.utils.galaxy.safe_fetch')

@pytest.fixture
def mock_paginated_results(mocker):
    return mocker.patch('galaxy_ng.app.utils.galaxy.paginated_results')

@pytest.fixture
def mock_find_namespace(mocker):
    return mocker.patch('galaxy_ng.app.utils.galaxy.find_namespace')

@pytest.fixture
def mock_get_namespace_owners_details(mocker):
    return mocker.patch('galaxy_ng.app.utils.galaxy.get_namespace_owners_details')

@pytest.fixture
def mock_upstream_namespace_iterator(mocker):
    return mocker.patch('galaxy_ng.app.utils.galaxy.upstream_namespace_iterator')

@pytest.fixture
def mock_upstream_collection_iterator(mocker):
    return mocker.patch('galaxy_ng.app.utils.galaxy.upstream_collection_iterator')

@pytest.fixture
def mock_upstream_role_iterator(mocker):
    return mocker.patch('galaxy_ng.app.utils.galaxy.upstream_role_iterator')

class TestGalaxyUtils:
    def test_generate_unverified_email(self):
        github_id = '1234567890'
        expected_email = f'{github_id}@GALAXY.GITHUB.UNVERIFIED.COM'
        assert generate_unverified_email(github_id) == expected_email

    def test_uuid_to_int(self):
        uuid = '12345678-1234-1234-1234-123456789012'
        expected_int = int(uuid.replace('-', ''), 16)
        assert uuid_to_int(uuid) == expected_int

    def test_int_to_uuid(self):
        int_value = 12345678901234567890
        expected_uuid = '12345678-1234-1234-1234-123456789012'
        assert int_to_uuid(int_value) == expected_uuid

    def test_safe_fetch_success(self, mock_safe_fetch):
        mock_safe_fetch.return_value.status_code = 200
        mock_safe_fetch.return_value.json.return_value = {'key': 'value'}
        result = safe_fetch('https://example.com')
        assert result.status_code == 200
        assert result.json() == {'key': 'value'}

    def test_safe_fetch_failure(self, mock_safe_fetch):
        mock_safe_fetch.return_value.status_code = 500
        mock_safe_fetch.return_value.json.return_value = {'error': 'test'}
        result = safe_fetch('https://example.com')
        assert result.status_code == 500
        assert result.json() == {'error': 'test'}

    def test_paginated_results_success(self, mock_paginated_results):
        mock_paginated_results.return_value = [{'key': 'value'}]
        result = paginated_results('https://example.com')
        assert result == [{'key': 'value'}]

    def test_paginated_results_failure(self, mock_paginated_results):
        mock_paginated_results.return_value = None
        result = paginated_results('https://example.com')
        assert result is None

    def test_find_namespace_success(self, mock_find_namespace):
        mock_find_namespace.return_value = ('namespace', {'key': 'value'})
        result = find_namespace('https://example.com', 'namespace')
        assert result == ('namespace', {'key': 'value'})

    def test_find_namespace_failure(self, mock_find_namespace):
        mock_find_namespace.return_value = None
        result = find_namespace('https://example.com', 'namespace')
        assert result is None

    def test_get_namespace_owners_details_success(self, mock_get_namespace_owners_details):
        mock_get_namespace_owners_details.return_value = [{'key': 'value'}]
        result = get_namespace_owners_details('https://example.com', 'namespace')
        assert result == [{'key': 'value'}]

    def test_get_namespace_owners_details_failure(self, mock_get_namespace_owners_details):
        mock_get_namespace_owners_details.return_value = None
        result = get_namespace_owners_details('https://example.com', 'namespace')
        assert result is None

    def test_upstream_namespace_iterator_success(self, mock_upstream_namespace_iterator):
        mock_upstream_namespace_iterator.return_value = [{'key': 'value'}]
        result = upstream_namespace_iterator('https://example.com')
        assert result == [{'key': 'value'}]

    def test_upstream_namespace_iterator_failure(self, mock_upstream_namespace_iterator):
        mock_upstream_namespace_iterator.return_value = None
        result = upstream_namespace_iterator('https://example.com')
        assert result is None

    def test_upstream_collection_iterator_success(self, mock_upstream_collection_iterator):
        mock_upstream_collection_iterator.return_value = [{'key': 'value'}]
        result = upstream_collection_iterator('https://example.com')
        assert result == [{'key': 'value'}]

    def test_upstream_collection_iterator_failure(self, mock_upstream_collection_iterator):
        mock_upstream_collection_iterator.return_value = None
        result = upstream_collection_iterator('https://example.com')
        assert result is None

    def test_upstream_role_iterator_success(self, mock_upstream_role_iterator):
        mock_upstream_role_iterator.return_value = [{'key': 'value'}]
        result = upstream_role_iterator('https://example.com')
        assert result == [{'key': 'value'}]

    def test_upstream_role_iterator_failure(self, mock_upstream_role_iterator):
        mock_upstream_role_iterator.return_value = None
        result = upstream_role_iterator('https://example.com')
        assert result is None
