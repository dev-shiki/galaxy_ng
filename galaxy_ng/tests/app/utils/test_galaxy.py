
import os
import sys
import pytest
from unittest import mock

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")

# Mock problematic modules
sys.modules["pulp_smash"] = mock.MagicMock()
import pytest
import logging
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse
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


@pytest.fixture
def mock_requests_get():
    with patch('requests.get') as mock_get:
        yield mock_get


@pytest.fixture
def mock_logger():
    with patch('galaxy_ng.app.utils.galaxy.logger') as mock_logger:
        yield mock_logger


def test_generate_unverified_email():
    assert generate_unverified_email(12345) == '12345@GALAXY.GITHUB.UNVERIFIED.COM'


def test_uuid_to_int():
    assert uuid_to_int('123e4567-e89b-12d3-a456-426614174000') == 291531444228056947960684030948500623040


def test_int_to_uuid():
    assert int_to_uuid(291531444228056947960684030948500623040) == '123e4567-e89b-12d3-a456-426614174000'


def test_safe_fetch_success(mock_requests_get, mock_logger):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests_get.return_value = mock_response
    response = safe_fetch('http://example.com')
    assert response == mock_response
    mock_logger.info.assert_called_with('fetch http://example.com')


def test_safe_fetch_retry(mock_requests_get, mock_logger):
    mock_response_500 = MagicMock()
    mock_response_500.status_code = 500
    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_requests_get.side_effect = [mock_response_500, mock_response_200]
    response = safe_fetch('http://example.com')
    assert response == mock_response_200
    mock_logger.info.assert_called_with('ERROR:500 waiting 60s to refetch http://example.com')


def test_safe_fetch_max_retries(mock_requests_get, mock_logger):
    mock_response_500 = MagicMock()
    mock_response_500.status_code = 500
    mock_requests_get.return_value = mock_response_500
    response = safe_fetch('http://example.com')
    assert response == mock_response_500
    assert mock_requests_get.call_count == 5


def test_paginated_results_success(mock_requests_get, mock_logger):
    mock_response_1 = MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {'results': [1, 2], 'next': 'http://example.com/page2'}
    mock_response_2 = MagicMock()
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {'results': [3, 4], 'next': None}
    mock_requests_get.side_effect = [mock_response_1, mock_response_2]
    results = paginated_results('http://example.com')
    assert results == [1, 2, 3, 4]
    mock_logger.info.assert_called_with('pagination fetch http://example.com/page2')


def test_paginated_results_404(mock_requests_get, mock_logger):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_requests_get.return_value = mock_response
    results = paginated_results('http://example.com')
    assert results == []
    mock_logger.info.assert_called_with('pagination fetch http://example.com')


def test_find_namespace_by_name(mock_requests_get, mock_logger):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'results': [{'name': 'test', 'id': 1}]}
    mock_requests_get.return_value = mock_response
    ns_name, ns_info = find_namespace(name='test')
    assert ns_name == 'test'
    assert ns_info['id'] == 1
    mock_logger.info.assert_called_with('find_namespace baseurl:https://old-galaxy.ansible.com name:test id:None')


def test_find_namespace_by_id(mock_requests_get, mock_logger):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'name': 'test', 'id': 1}
    mock_requests_get.return_value = mock_response
    ns_name, ns_info = find_namespace(id=1)
    assert ns_name == 'test'
    assert ns_info['id'] == 1
    mock_logger.info.assert_called_with('find_namespace baseurl:https://old-galaxy.ansible.com name:None id:1')


def test_get_namespace_owners_details(mock_requests_get, mock_logger):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'results': [{'id': 1, 'username': 'owner1'}]}
    mock_requests_get.return_value = mock_response
    owners = get_namespace_owners_details('https://old-galaxy.ansible.com', 1)
    assert owners == [{'id': 1, 'username': 'owner1'}]
    mock_logger.info.assert_called_with('fetch https://old-galaxy.ansible.com/api/v1/namespaces/1/owners/')


def test_upstream_namespace_iterator(mock_requests_get, mock_logger):
    mock_response_1 = MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {'count': 2, 'results': [{'id': 1, 'summary_fields': {'content_counts': {}}}, {'id': 2, 'summary_fields': {'content_counts': {}}}], 'next_link': 'http://example.com/page2'}
    mock_response_2 = MagicMock()
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {'count': 2, 'results': [{'id': 3, 'summary_fields': {'content_counts': {}}}], 'next_link': None}
    mock_requests_get.side_effect = [mock_response_1, mock_response_2]
    iterator = upstream_namespace_iterator()
    results = list(iterator)
    assert len(results) == 1
    mock_logger.info.assert_called_with('fetch 1 http://example.com/page2')


def test_upstream_collection_iterator(mock_requests_get, mock_logger):
    mock_response_1 = MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {'count': 2, 'results': [{'id': 1, 'namespace': {'id': 1}, 'versions_url': 'http://example.com/versions1'}], 'next_link': 'http://example.com/page2'}
    mock_response_2 = MagicMock()
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {'count': 2, 'results': [{'id': 2, 'namespace': {'id': 2}, 'versions_url': 'http://example.com/versions2'}], 'next_link': None}
    mock_response_versions = MagicMock()
    mock_response_versions.status_code = 200
    mock_response_versions.json.return_value = [{'version': '1.0.0'}]
    mock_requests_get.side_effect = [mock_response_1, mock_response_2, mock_response_versions, mock_response_versions]
    iterator = upstream_collection_iterator()
    results = list(iterator)
    assert len(results) == 2
    mock_logger.info.assert_called_with('fetch 1 http://example.com/page2')


def test_upstream_role_iterator(mock_requests_get, mock_logger):
    mock_response_1 = MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {'count': 2, 'results': [{'id': 1, 'summary_fields': {'namespace': {'id': 1}}}], 'next_link': 'http://example.com/page2'}
    mock_response_2 = MagicMock()
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {'count': 2, 'results': [{'id': 2, 'summary_fields': {'namespace': {'id': 2}}}], 'next_link': None}
    mock_response_role = MagicMock()
    mock_response_role.status_code = 200
    mock_response_role.json.return_value = {'id': 1, 'summary_fields': {'namespace': {'id': 1}}}
    mock_response_versions = MagicMock()
    mock_response_versions.status_code = 200
    mock_response_versions.json.return_value = [{'version': '1.0.0'}]
    mock_requests_get.side_effect = [mock_response_1, mock_response_2, mock_response_role, mock_response_versions, mock_response_role, mock_response_versions]
    iterator = upstream_role_iterator()
    results = list(iterator)
    assert len(results) == 2
    mock_logger.info.assert_called_with('fetch 1 http://example.com/page2')
