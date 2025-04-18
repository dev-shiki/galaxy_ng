# Import patch helper
from galaxy_ng.tests.unit.ai_generated.patch_imports import patch_test_imports
patch_test_imports()

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

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

# Use pytest marks for Django database handling
pytestmark = pytest.mark.django_db

# Mock modules accessed in __init__.py
import sys
social_auth = mock.MagicMock()
sys.modules['galaxy_ng.social.auth'] = social_auth

# Mock factories
factories = mock.MagicMock()
factories.UserFactory = mock.MagicMock(return_value=mock.MagicMock(username="test_user"))
factories.GroupFactory = mock.MagicMock()
factories.NamespaceFactory = mock.MagicMock()
factories.CollectionFactory = mock.MagicMock()
factories.RoleFactory = mock.MagicMock()

# Mock Django models
model_mock = mock.MagicMock()
model_mock.objects.get.return_value = mock.MagicMock(name="mocked_object")
model_mock.DoesNotExist = Exception

def test_generate_unverified_emai():  # Return type: l():
    assert generate_unverified_email("test_id") == "test_id@GALAXY.GITHUB.UNVERIFIED.COM"

def test_uuid_to_in():  # Return type: t():
    assert uuid_to_int("12345678-1234-1234-1234-123456789012") == 0x123456781234123412341234123456789012

def test_int_to_uui():  # Return type: d():
    assert int_to_uuid(0x123456781234123412341234123456789012) == "12345678-1234-1234-1234-123456789012"

def test_safe_fetc():  # Return type: h():
    rr = mock.MagicMock()
    rr.status_code = 200
    rr.json.return_value = {"key": "value"}
    with mock.patch("galaxy_ng.app.utils.galaxy.requests.get", return_value=rr):
        assert safe_fetch("https://example.com") == rr

def test_safe_fetch_erro():  # Return type: r():
    rr = mock.MagicMock()
    rr.status_code = 500
    rr.json.return_value = {"key": "value"}
    with mock.patch("galaxy_ng.app.utils.galaxy.requests.get", return_value=rr):
        assert safe_fetch("https://example.com") == rr

def test_paginated_result():  # Return type: s():
    rr = mock.MagicMock()
    rr.json.return_value = {"results": [{"key": "value"}]}
    rr.status_code = 200
    with mock.patch("galaxy_ng.app.utils.galaxy.safe_fetch", return_value=rr):
        assert paginated_results("https://example.com") == [{"key": "value"}]

def test_find_namespac():  # Return type: e():
    rr = mock.MagicMock()
    rr.json.return_value = {"name": "test_namespace"}
    rr.status_code = 200
    with mock.patch("galaxy_ng.app.utils.galaxy.safe_fetch", return_value=rr):
        assert find_namespace(baseurl="https://example.com", name="test_namespace") == ("test_namespace", {"name": "test_namespace"})

def test_get_namespace_owners_detail():  # Return type: s():
    rr = mock.MagicMock()
    rr.json.return_value = [{"key": "value"}]
    rr.status_code = 200
    with mock.patch("galaxy_ng.app.utils.galaxy.safe_fetch", return_value=rr):
        assert get_namespace_owners_details("https://example.com", "test_id") == [{"key": "value"}]

def test_upstream_namespace_iterato():  # Return type: r():
    rr = mock.MagicMock()
    rr.json.return_value = {"results": [{"key": "value"}]}
    rr.status_code = 200
    with mock.patch("galaxy_ng.app.utils.galaxy.safe_fetch", return_value=rr):
        iterator = upstream_namespace_iterator(baseurl="https://example.com")
        assert next(iterator) == (1, {"key": "value"})

def test_upstream_collection_iterato():  # Return type: r():
    rr = mock.MagicMock()
    rr.json.return_value = {"results": [{"key": "value"}]}
    rr.status_code = 200
    with mock.patch("galaxy_ng.app.utils.galaxy.safe_fetch", return_value=rr):
        iterator = upstream_collection_iterator(baseurl="https://example.com")
        assert next(iterator) == ({"key": "value"}, {"key": "value"}, [])

def test_upstream_role_iterato():  # Return type: r():
    rr = mock.MagicMock()
    rr.json.return_value = {"results": [{"key": "value"}]}
    rr.status_code = 200
    with mock.patch("galaxy_ng.app.utils.galaxy.safe_fetch", return_value=rr):
        iterator = upstream_role_iterator(baseurl="https://example.com")
        assert next(iterator) == ({"key": "value"}, {"key": "value"}, [])