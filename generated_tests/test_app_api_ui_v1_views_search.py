import pytest
from django.contrib.postgres.search import SearchQuery
from django.db.models import Q, Value, FloatField, Func, JSONField, OuterRef, Subquery, Exists
from django.db.models.functions import Coalesce, JSONBAgg
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import MagicMock, patch
from galaxy_ng.app.api.ui.v1.views.search import SearchListView
from galaxy_ng.app.api.ui.v1.serializers import SearchResultsSerializer
from galaxy_ng.app.models.namespace import Namespace
from pulp_ansible.app.models import (
    AnsibleCollectionDeprecated,
    CollectionDownloadCount,
    CollectionVersion,
    LegacyRole,
    LegacyRoleDownloadCount,
    LegacyRoleSearchVector,
)


@pytest.fixture
def mock_collection_version():
    return CollectionVersion.objects.create(
        namespace="test_namespace",
        name="test_collection",
        version="1.0.0",
        description="Test Collection",
        timestamp_of_interest="2023-11-09T15:17:01.235457Z",
        is_highest=True,
    )


@pytest.fixture
def mock_legacy_role():
    return LegacyRole.objects.create(
        namespace_id=1,
        name="test_role",
        created="2023-11-09T15:17:01.235457Z",
        full_metadata={
            "description": "Test Role",
            "platforms": ["Ubuntu"],
            "tags": ["test"],
            "versions": [{"version": "1.0.0"}],
        },
    )


@pytest.fixture
def mock_namespace():
    return Namespace.objects.create(name="test_namespace", _avatar_url="http://example.com/avatar")


@pytest.fixture
def mock_collection_download_count(mock_collection_version):
    return CollectionDownloadCount.objects.create(
        namespace=mock_collection_version.namespace,
        name=mock_collection_version.name,
        download_count=100,
    )


@pytest.fixture
def mock_ansible_collection_deprecated(mock_collection_version):
    return AnsibleCollectionDeprecated.objects.create(
        namespace=mock_collection_version.namespace,
        name=mock_collection_version.name,
    )


@pytest.fixture
def mock_legacy_role_download_count(mock_legacy_role):
    return LegacyRoleDownloadCount.objects.create(
        role=mock_legacy_role,
        count=50,
    )


@pytest.fixture
def mock_legacy_role_search_vector(mock_legacy_role):
    return LegacyRoleSearchVector.objects.create(
        role=mock_legacy_role,
        search_vector=SearchQuery("test"),
    )


@pytest.mark.django_db
class TestSearchListView(APITestCase):
    def setUp(self):
        self.url = reverse("galaxy:ui:v1:search-list")

    def test_list_no_params(self, mock_collection_version, mock_legacy_role):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_keywords(self, mock_collection_version, mock_legacy_role):
        response = self.client.get(self.url, {"keywords": "test"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_type_collection(self, mock_collection_version):
        response = self.client.get(self.url, {"type": "collection"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_type_role(self, mock_legacy_role):
        response = self.client.get(self.url, {"type": "role"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_invalid_type(self):
        response = self.client.get(self.url, {"type": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_with_deprecated_true(self, mock_collection_version, mock_ansible_collection_deprecated):
        response = self.client.get(self.url, {"deprecated": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_deprecated_false(self, mock_collection_version):
        response = self.client.get(self.url, {"deprecated": "false"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_invalid_deprecated(self):
        response = self.client.get(self.url, {"deprecated": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_with_name(self, mock_collection_version):
        response = self.client.get(self.url, {"name": "test_collection"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_namespace(self, mock_collection_version):
        response = self.client.get(self.url, {"namespace": "test_namespace"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_tags(self, mock_collection_version, mock_legacy_role):
        response = self.client.get(self.url, {"tags": "test"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_platform(self, mock_collection_version, mock_legacy_role):
        response = self.client.get(self.url, {"platform": "Ubuntu"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_order_by(self, mock_collection_version, mock_legacy_role):
        response = self.client.get(self.url, {"order_by": "-download_count"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_invalid_order_by(self):
        response = self.client.get(self.url, {"order_by": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_with_relevance_order_by(self, mock_collection_version, mock_legacy_role):
        response = self.client.get(self.url, {"order_by": "-relevance", "search_type": "websearch"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_list_with_invalid_relevance_order_by(self, mock_collection_version, mock_legacy_role):
        response = self.client.get(self.url, {"order_by": "-relevance", "search_type": "sql"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_filter_params(self):
        request = MagicMock()
        request.query_params = {
            "keywords": "test",
            "type": "collection",
            "deprecated": "true",
            "name": "test_collection",
            "namespace": "test_namespace",
            "tags": ["test"],
            "platform": "Ubuntu",
            "order_by": "-download_count",
        }
        view = SearchListView()
        view.request = request
        filter_params = view.get_filter_params(request)
        expected_params = {
            "keywords": "test",
            "type": "collection",
            "deprecated": "true",
            "name": "test_collection",
            "namespace": "test_namespace",
            "tags": ["test"],
            "platform": "Ubuntu",
        }
        self.assertEqual(filter_params, expected_params)

    def test_get_sorting_param(self):
        request = MagicMock()
        request.query_params = {"order_by": "-download_count,-relevance", "search_type": "websearch"}
        view = SearchListView()
        view.request = request
        sort = view.get_sorting_param(request)
        expected_sort = ["-download_count", "-relevance"]
        self.assertEqual(sort, expected_sort)

    def test_get_sorting_param_invalid(self):
        request = MagicMock()
        request.query_params = {"order_by": "invalid", "search_type": "websearch"}
        view = SearchListView()
        view.request = request
        with self.assertRaises(ValidationError):
            view.get_sorting_param(request)

    def test_get_collection_queryset(self, mock_collection_version, mock_collection_download_count, mock_ansible_collection_deprecated, mock_namespace):
        view = SearchListView()
        query = SearchQuery("test", search_type="websearch")
        qs = view.get_collection_queryset(query=query)
        self.assertEqual(qs.count(), 1)

    def test_get_role_queryset(self, mock_legacy_role, mock_legacy_role_download_count, mock_legacy_role_search_vector):
        view = SearchListView()
        query = SearchQuery("test", search_type="websearch")
        qs = view.get_role_queryset(query=query)
        self.assertEqual(qs.count(), 1)

    def test_filter_and_sort(self, mock_collection_version, mock_ansible_collection_deprecated, mock_namespace, mock_legacy_role, mock_legacy_role_download_count, mock_legacy_role_search_vector):
        view = SearchListView()
        collections = view.get_collection_queryset()
        roles = view.get_role_queryset()
        filter_params = {
            "deprecated": "true",
            "name": "test_collection",
            "namespace": "test_namespace",
            "tags": ["test"],
            "platform": "Ubuntu",
        }
        sort = ["-download_count", "-relevance"]
        qs = view.filter_and_sort(collections, roles, filter_params, sort)
        self.assertEqual(qs.count(), 1)

    def test_filter_and_sort_invalid_deprecated(self, mock_collection_version, mock_ansible_collection_deprecated, mock_namespace, mock_legacy_role, mock_legacy_role_download_count, mock_legacy_role_search_vector):
        view = SearchListView()
        collections = view.get_collection_queryset()
        roles = view.get_role_queryset()
        filter_params = {
            "deprecated": "invalid",
        }
        sort = ["-download_count", "-relevance"]
        with self.assertRaises(ValidationError):
            view.filter_and_sort(collections, roles, filter_params, sort)

    @patch("galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_collection_queryset")
    @patch("galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_role_queryset")
    def test_get_search_results(self, mock_get_role_queryset, mock_get_collection_queryset, mock_collection_version, mock_ansible_collection_deprecated, mock_namespace, mock_legacy_role, mock_legacy_role_download_count, mock_legacy_role_search_vector):
        view = SearchListView()
        mock_get_collection_queryset.return_value = view.get_collection_queryset()
        mock_get_role_queryset.return_value = view.get_role_queryset()
        filter_params = {
            "type": "collection",
            "search_type": "websearch",
            "keywords": "test",
        }
        sort = ["-download_count", "-relevance"]
        qs = view.get_search_results(filter_params, sort)
        self.assertEqual(qs.count(), 1)

    @patch("galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_collection_queryset")
    @patch("galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_role_queryset")
    def test_get_search_results_invalid_type(self, mock_get_role_queryset, mock_get_collection_queryset):
        view = SearchListView()
        mock_get_collection_queryset.return_value = view.get_collection_queryset()
        mock_get_role_queryset.return_value = view.get_role_queryset()
        filter_params = {
            "type": "invalid",
            "search_type": "websearch",
            "keywords": "test",
        }
        sort = ["-download_count", "-relevance"]
        with self.assertRaises(ValidationError):
            view.get_search_results(filter_params, sort)

    @patch("galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_collection_queryset")
    @patch("galaxy_ng.app.api.ui.v1.views.search.SearchListView.get_role_queryset")
    def test_get_search_results_invalid_search_type(self, mock_get_role_queryset, mock_get_collection_queryset):
        view = SearchListView()
        mock_get_collection_queryset.return_value = view.get_collection_queryset()
        mock_get_role_queryset.return_value = view.get_role_queryset()
        filter_params = {
            "type": "collection",
            "search_type": "invalid",
            "keywords": "test",
        }
        sort = ["-download_count", "-relevance"]
        with self.assertRaises(ValidationError):
            view.get_search_results(filter_params, sort)
