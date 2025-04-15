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

import os
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

import pytest
from unittest import mock
from galaxy_ng.app.api.ui.v1.views import search
from galaxy_ng.app.api.ui.v1.serializers import SearchResultsSerializer
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.models.namespace import Namespace
from rest_framework.test import APIClient
from rest_framework import status

@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def mock_queryset():
    class MockQuerySet:
        def __init__(self, data):
            self.data = data

        def filter(self, *args, **kwargs):
            return self

        def annotate(self, *args, **kwargs):
            return self

        def values(self, *args, **kwargs):
            return self

        def union(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def count(self):
            return len(self.data)

        def __getitem__(self, key):
            return self.data[key]

    return MockQuerySet([])

@pytest.fixture
def mock_filter_params():
    return {"type": "collection", "keywords": "test", "deprecated": "true"}

@pytest.fixture
def mock_sort():
    return ["name", "-relevance"]

def test_search_list_view(client, mock_queryset, mock_filter_params, mock_sort):
    view = search.SearchListView()
    view.request = mock.Mock()
    view.request.query_params = mock_filter_params
    view.request.query_params._mutable = True
    view.request.query_params["order_by"] = ",".join(mock_sort)
    view.request.query_params._mutable = False
    view.get_queryset = mock.Mock(return_value=mock_queryset)
    response = view.list()
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0

def test_get_search_results(mock_queryset, mock_filter_params, mock_sort):
    view = search.SearchListView()
    view.filter_params = mock_filter_params
    view.sort = mock_sort
    view.get_queryset = mock.Mock(return_value=mock_queryset)
    result = view.get_search_results(mock_filter_params, mock_sort)
    assert result == mock_queryset

def test_get_filter_params(client):
    view = search.SearchListView()
    view.request = client
    view.request.query_params = {"type": "collection", "keywords": "test", "deprecated": "true"}
    result = view.get_filter_params(view.request)
    assert result == {"type": "collection", "keywords": "test", "deprecated": "true"}

def test_get_sorting_param(client):
    view = search.SearchListView()
    view.request = client
    view.request.query_params = {"type": "collection", "keywords": "test", "deprecated": "true", "order_by": "name,-relevance"}
    result = view.get_sorting_param(view.request)
    assert result == ["name", "-relevance"]

def test_get_collection_queryset(mock_queryset):
    view = search.SearchListView()
    view.get_queryset = mock.Mock(return_value=mock_queryset)
    result = view.get_collection_queryset()
    assert result == mock_queryset

def test_get_role_queryset(mock_queryset):
    view = search.SearchListView()
    view.get_queryset = mock.Mock(return_value=mock_queryset)
    result = view.get_role_queryset()
    assert result == mock_queryset

def test_filter_and_sort(mock_queryset, mock_filter_params, mock_sort):
    view = search.SearchListView()
    view.filter_params = mock_filter_params
    view.sort = mock_sort
    view.get_queryset = mock.Mock(return_value=mock_queryset)
    result = view.filter_and_sort(mock_queryset, mock_queryset, mock_filter_params, mock_sort)
    assert result == mock_queryset

def test_get_search_results_invalid_search_type(mock_queryset, mock_filter_params, mock_sort):
    view = search.SearchListView()
    view.filter_params = mock_filter_params
    view.sort = mock_sort
    view.get_queryset = mock.Mock(return_value=mock_queryset)
    with pytest.raises(search.ValidationError):
        view.get_search_results(mock_filter_params, mock_sort, search_type="invalid")

def test_get_search_results_invalid_type(mock_queryset, mock_filter_params, mock_sort):
    view = search.SearchListView()
    view.filter_params = mock_filter_params
    view.sort = mock_sort
    view.get_queryset = mock.Mock(return_value=mock_queryset)
    with pytest.raises(search.ValidationError):
        view.get_search_results(mock_filter_params, mock_sort, type="invalid")

def test_get_search_results_invalid_sort(mock_queryset, mock_filter_params, mock_sort):
    view = search.SearchListView()
    view.filter_params = mock_filter_params
    view.sort = mock_sort
    view.get_queryset = mock.Mock(return_value=mock_queryset)
    with pytest.raises(search.ValidationError):
        view.get_search_results(mock_filter_params, ["invalid", "sort"], search_type="websearch")

def test_get_sorting_param_invalid_sort(mock_queryset, mock_filter_params, mock_sort):
    view = search.SearchListView()
    view.request = mock.Mock()
    view.request.query_params = {"type": "collection", "keywords": "test", "deprecated": "true", "order_by": "invalid"}
    with pytest.raises(search.ValidationError):
        view.get_sorting_param(view.request)

def test_get_sorting_param_invalid_search_type(mock_queryset, mock_filter_params, mock_sort):
    view = search.SearchListView()
    view.request = mock.Mock()
    view.request.query_params = {"type": "collection", "keywords": "test", "deprecated": "true", "order_by": "name,-relevance", "search_type": "invalid"}
    with pytest.raises(search.ValidationError):
        view.get_sorting_param(view.request)
