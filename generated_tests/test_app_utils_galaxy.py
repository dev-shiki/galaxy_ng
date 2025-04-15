import pytest
from galaxy_ng.app.utils.galaxy import (
    generate_unverified_email,
    uuid_to_int,
    int_to_uuid,
    safe_fetch,
    paginated_results,
    ,
    find_namespace,
    get_namespace_owners_details,
    upstream_namespace_iterator,
    upstream_collection_iterator,
    upstream_role_iterator
)
from unittest.mock import patch, MagicMock
from requests import Response
from urllib.parse import urlparse
import logging
import json

@pytest.fixture
def mock_logger():
    with patch.object(logging.getLogger(__name__), 'info') as mock_info:
        yield mock_info

@pytest.fixture
def mock_safe_fetch():
    with patch.object(galaxy, 'safe_fetch') as mock_safe_fetch:
        yield mock_safe_fetch

@pytest.fixture
def mock_paginated_results():
    with patch.object(galaxy, 'paginated_results') as mock_paginated_results:
        yield mock_paginated_results

@pytest.fixture
def mock_find_namespace():
    with patch.object(galaxy, 'find_namespace') as mock_find_namespace:
        yield mock_find_namespace

@pytest.fixture
def mock_get_namespace_owners_details():
    with patch.object(galaxy, 'get_namespace_owners_details') as mock_get_namespace_owners_details:
        yield mock_get_namespace_owners_details

@pytest.fixture
def mock_upstream_namespace_iterator():
    with patch.object(galaxy, 'upstream_namespace_iterator') as mock_upstream_namespace_iterator:
        yield mock_upstream_namespace_iterator

@pytest.fixture
def mock_upstream_collection_iterator():
    with patch.object(galaxy, 'upstream_collection_iterator') as mock_upstream_collection_iterator:
        yield mock_upstream_collection_iterator

@pytest.fixture
def mock_upstream_role_iterator():
    with patch.object(galaxy, 'upstream_role_iterator') as mock_upstream_role_iterator:
        yield mock_upstream_role_iterator

@pytest.fixture
def galaxy():
    galaxy = MagicMock()
    galaxy.safe_fetch = MagicMock()
    galaxy.paginated_results = MagicMock()
    galaxy.find_namespace = MagicMock()
    galaxy.get_namespace_owners_details = MagicMock()
    galaxy.upstream_namespace_iterator = MagicMock()
    galaxy.upstream_collection_iterator = MagicMock()
    galaxy.upstream_role_iterator = MagicMock()
    return galaxy

def test_generate_unverified_email():
    assert generate_unverified_email('1234567890') == '1234567890@GALAXY.GITHUB.UNVERIFIED.COM'

def test_uuid_to_int():
    assert uuid_to_int('12345678-1234-1234-1234-123456789012') == 0x123456781234123412341234123456789012

def test_int_to_uuid():
    assert int_to_uuid(0x123456781234123412341234123456789012) == '12345678-1234-1234-1234-123456789012'

def test_safe_fetch_success(mock_safe_fetch):
    mock_safe_fetch.return_value = Response(status_code=200)
    assert safe_fetch('https://example.com') == Response(status_code=200)

def test_safe_fetch_failure(mock_safe_fetch):
    mock_safe_fetch.return_value = Response(status_code=500)
    with pytest.raises(Exception):
        safe_fetch('https://example.com')

def test_safe_fetch_retry(mock_safe_fetch):
    mock_safe_fetch.side_effect = [Response(status_code=500), Response(status_code=200)]
    assert safe_fetch('https://example.com') == Response(status_code=200)

def test_paginated_results_success(mock_paginated_results):
    mock_paginated_results.return_value = [{'results': [{'key': 'value'}]}]
    assert paginated_results('https://example.com') == [{'results': [{'key': 'value'}]}]

def test_paginated_results_failure(mock_paginated_results):
    mock_paginated_results.return_value = [{'results': [{'key': 'value'}]}]
    with pytest.raises(Exception):
        paginated_results('https://example.com')

def test_find_namespace_success(mock_find_namespace):
    mock_find_namespace.return_value = ('namespace', {'id': 1, 'name': 'namespace'})
    assert find_namespace('https://example.com', 'namespace') == ('namespace', {'id': 1, 'name': 'namespace'})

def test_find_namespace_failure(mock_find_namespace):
    mock_find_namespace.return_value = None
    with pytest.raises(Exception):
        find_namespace('https://example.com', 'namespace')

def test_get_namespace_owners_details_success(mock_get_namespace_owners_details):
    mock_get_namespace_owners_details.return_value = [{'id': 1, 'name': 'owner'}]
    assert get_namespace_owners_details('https://example.com', 1) == [{'id': 1, 'name': 'owner'}]

def test_get_namespace_owners_details_failure(mock_get_namespace_owners_details):
    mock_get_namespace_owners_details.return_value = None
    with pytest.raises(Exception):
        get_namespace_owners_details('https://example.com', 1)

def test_upstream_namespace_iterator_success(mock_upstream_namespace_iterator):
    mock_upstream_namespace_iterator.return_value = [{'total': 1, 'data': {'id': 1, 'name': 'namespace'}}]
    assert list(upstream_namespace_iterator('https://example.com')) == [{'total': 1, 'data': {'id': 1, 'name': 'namespace'}}]

def test_upstream_namespace_iterator_failure(mock_upstream_namespace_iterator):
    mock_upstream_namespace_iterator.return_value = None
    with pytest.raises(Exception):
        list(upstream_namespace_iterator('https://example.com'))

def test_upstream_collection_iterator_success(mock_upstream_collection_iterator):
    mock_upstream_collection_iterator.return_value = [{'namespace': {'id': 1, 'name': 'namespace'}, 'data': {'id': 1, 'name': 'collection'}, 'versions': [{'id': 1, 'name': 'version'}]}]
    assert list(upstream_collection_iterator('https://example.com')) == [{'namespace': {'id': 1, 'name': 'namespace'}, 'data': {'id': 1, 'name': 'collection'}, 'versions': [{'id': 1, 'name': 'version'}]}]

def test_upstream_collection_iterator_failure(mock_upstream_collection_iterator):
    mock_upstream_collection_iterator.return_value = None
    with pytest.raises(Exception):
        list(upstream_collection_iterator('https://example.com'))

def test_upstream_role_iterator_success(mock_upstream_role_iterator):
    mock_upstream_role_iterator.return_value = [{'namespace': {'id': 1, 'name': 'namespace'}, 'data': {'id': 1, 'name': 'role'}, 'versions': [{'id': 1, 'name': 'version'}]}]
    assert list(upstream_role_iterator('https://example.com')) == [{'namespace': {'id': 1, 'name': 'namespace'}, 'data': {'id': 1, 'name': 'role'}, 'versions': [{'id': 1, 'name': 'version'}]}]

def test_upstream_role_iterator_failure(mock_upstream_role_iterator):
    mock_upstream_role_iterator.return_value = None
    with pytest.raises(Exception):
        list(upstream_role_iterator('https://example.com'))
