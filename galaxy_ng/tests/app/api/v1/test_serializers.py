import sys

# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")
from django.conf import settingsimport pytest
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError
from galaxy_ng.app.api.v1.serializers import (
    LegacyNamespacesSerializer,
    LegacyNamespaceOwnerSerializer,
    LegacyNamespaceProviderSerializer,
    LegacyUserSerializer,
    LegacyRoleSerializer,
    LegacyRoleRepositoryUpdateSerializer,
    LegacyRoleUpdateSerializer,
    LegacyRoleContentSerializer,
    LegacyRoleVersionsSerializer,
    LegacyImportSerializer,
    LegacyImportListSerializer,
    LegacySyncSerializer,
    LegacySyncTaskResponseSerializer,
    LegacyTaskQuerySerializer,
    LegacyTaskSummaryTaskMessagesFieldsSerializer,
    LegacyTaskSummaryFieldsSerializer,
    LegacyTaskResultsSerializer,
    LegacyTaskDetailSerializer,
    LegacyRoleImportDetailSerializer,
    LegacyRoleTagSerializer,
)
from galaxy_ng.app.models.auth import User
from galaxy_ng.app.models.namespace import Namespace
from galaxy_ng.app.models import LegacyNamespace, LegacyRole, LegacyRoleTag, LegacyRoleDownloadCount
from galaxy_ng.app.utils.rbac import get_v3_namespace_owners
from galaxy_ng.app.utils.galaxy import uuid_to_int
from galaxy_ng.app.api.v1.utils import sort_versions


@pytest.fixture
def request_factory():
    return APIRequestFactory()


@pytest.fixture
def legacy_namespace():
    namespace = Namespace.objects.create(name="test_namespace")
    return LegacyNamespace.objects.create(namespace=namespace, name="test_legacy_namespace")


@pytest.fixture
def user():
    return User.objects.create(username="test_user")


@pytest.fixture
def legacy_role(legacy_namespace):
    return LegacyRole.objects.create(
        namespace=legacy_namespace,
        name="test_role",
        full_metadata={
            "upstream_id": "123",
            "imported": True,
            "github_user": "test_user",
            "github_repo": "test_repo",
            "github_reference": "main",
            "commit": "abc123",
            "commit_message": "Initial commit",
            "description": "Test role",
            "dependencies": [],
            "tags": [],
            "versions": [
                {"id": 1, "tag": "v1.0.0", "commit_date": "2023-01-01T00:00:00Z"},
                {"id": 2, "tag": "v1.1.0", "commit_date": "2023-02-01T00:00:00Z"},
            ],
        },
    )


@pytest.fixture
def legacy_role_tag():
    return LegacyRoleTag.objects.create(name="test_tag", count=5)


@pytest.fixture
def legacy_role_download_count(legacy_role):
    return LegacyRoleDownloadCount.objects.create(legacyrole=legacy_role, count=10)


@pytest.mark.django_db
def test_legacy_namespaces_serializer(legacy_namespace):
    serializer = LegacyNamespacesSerializer(legacy_namespace)
    data = serializer.data
    assert data["id"] == legacy_namespace.id
    assert data["name"] == legacy_namespace.name
    assert data["url"] == ""
    assert data["avatar_url"] == f"https://github.com/{legacy_namespace.name}.png"
    assert data["related"]["owners"] == f"/api/v1/namespaces/{legacy_namespace.id}/owners/"


@pytest.mark.django_db
def test_legacy_namespace_owner_serializer(user):
    serializer = LegacyNamespaceOwnerSerializer(user)
    data = serializer.data
    assert data["id"] == user.id


@pytest.mark.django_db
def test_legacy_namespace_provider_serializer(legacy_namespace):
    serializer = LegacyNamespaceProviderSerializer(legacy_namespace.namespace)
    data = serializer.data
    assert data["id"] == legacy_namespace.namespace.id
    assert data["name"] == legacy_namespace.namespace.name


@pytest.mark.django_db
def test_legacy_user_serializer(user):
    serializer = LegacyUserSerializer(user)
    data = serializer.data
    assert data["id"] == user.id
    assert data["username"] == user.username
    assert data["full_name"] == ""
    assert data["date_joined"] == user.date_joined
    assert data["avatar_url"] == f"https://github.com/{user.username}.png"
    assert data["github_id"] is None


@pytest.mark.django_db
def test_legacy_role_serializer(legacy_role):
    serializer = LegacyRoleSerializer(legacy_role)
    data = serializer.data
    assert data["id"] == legacy_role.pulp_id
    assert data["upstream_id"] == "123"
    assert data["github_user"] == "test_user"
    assert data["github_repo"] == "test_repo"
    assert data["github_branch"] == "main"
    assert data["commit"] == "abc123"
    assert data["commit_message"] == "Initial commit"
    assert data["description"] == "Test role"
    assert data["download_count"] == 10


@pytest.mark.django_db
def test_legacy_role_repository_update_serializer():
    data = {"name": "new_name", "original_name": "original_name"}
    serializer = LegacyRoleRepositoryUpdateSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

    data = {"name": "new_name", "unknown_field": "value"}
    serializer = LegacyRoleRepositoryUpdateSerializer(data=data)
    assert not serializer.is_valid()
    assert "unknown_field" in serializer.errors


@pytest.mark.django_db
def test_legacy_role_update_serializer():
    data = {
        "github_user": "new_user",
        "github_repo": "new_repo",
        "github_branch": "new_branch",
        "repository": {"name": "new_name", "original_name": "original_name"},
    }
    serializer = LegacyRoleUpdateSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

    data = {"github_user": "new_user", "unknown_field": "value"}
    serializer = LegacyRoleUpdateSerializer(data=data)
    assert not serializer.is_valid()
    assert "unknown_field" in serializer.errors


@pytest.mark.django_db
def test_legacy_role_content_serializer(legacy_role):
    serializer = LegacyRoleContentSerializer(legacy_role)
    data = serializer.data
    assert data["readme"] == ""
    assert data["readme_html"] == ""


@pytest.mark.django_db
def test_legacy_role_versions_serializer(legacy_role):
    serializer = LegacyRoleVersionsSerializer(legacy_role)
    data = serializer.data
    assert data["count"] == 2
    assert len(data["results"]) == 2
    assert data["results"][0]["name"] == "v1.1.0"
    assert data["results"][1]["name"] == "v1.0.0"


@pytest.mark.django_db
def test_legacy_import_serializer():
    data = {
        "github_user": "test_user",
        "github_repo": "test_repo",
        "alternate_namespace_name": "alt_namespace",
        "alternate_role_name": "alt_role",
        "alternate_clone_url": "https://github.com/test_user/test_repo",
        "github_reference": "main",
    }
    serializer = LegacyImportSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

    data = {"github_user": "test_user", "unknown_field": "value"}
    serializer = LegacyImportSerializer(data=data)
    assert not serializer.is_valid()
    assert "unknown_field" in serializer.errors


@pytest.mark.django_db
def test_legacy_import_list_serializer():
    task = MagicMock()
    task.pulp_id = "123"
    task.pulp_created = datetime.datetime.now()
    task.pulp_last_updated = datetime.datetime.now()
    task.state = "COMPLETED"
    task.enc_kwargs = {
        "request_username": "test_user",
        "github_user": "test_user",
        "github_repo": "test_repo",
        "github_reference": "main",
        "alternate_role_name": "alt_role",
    }
    obj = MagicMock(task=task)

    serializer = LegacyImportListSerializer(obj)
    data = serializer.data
    assert data["id"] == uuid_to_int(str(task.pulp_id))
    assert data["pulp_id"] == str(task.pulp_id)
    assert data["state"] == "SUCCESS"
    assert data["summary_fields"] == {
        "request_username": "test_user",
        "github_user": "test_user",
        "github_repo": "test_repo",
        "github_reference": "main",
        "alternate_role_name": "alt_role",
    }


@pytest.mark.django_db
def test_legacy_sync_serializer():
    data = {
        "baseurl": "https://old-galaxy.ansible.com/api/v1/roles/",
        "github_user": "test_user",
        "role_name": "test_role",
        "role_version": "v1.0.0",
        "limit": 10,
    }
    serializer = LegacySyncSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

    data = {"baseurl": "https://old-galaxy.ansible.com/api/v1/roles/", "unknown_field": "value"}
    serializer = LegacySyncSerializer(data=data)
    assert not serializer.is_valid()
    assert "unknown_field" in serializer.errors


@pytest.mark.django_db
def test_legacy_sync_task_response_serializer():
    data = {"task": "123"}
    serializer = LegacySyncTaskResponseSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

    data = {"unknown_field": "value"}
    serializer = LegacySyncTaskResponseSerializer(data=data)
    assert not serializer.is_valid()
    assert "unknown_field" in serializer.errors


@pytest.mark.django_db
def test_legacy_task_query_serializer():
    data = {"id": 123}
    serializer = LegacyTaskQuerySerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

    data = {"unknown_field": "value"}
    serializer = LegacyTaskQuerySerializer(data=data)
    assert not serializer.is_valid()
    assert "unknown_field" in serializer.errors


@pytest.mark.django_db
def test_legacy_task_summary_task_messages_fields_serializer():
    data = {
        "id": datetime.datetime.now().isoformat(),
        "message_type": "INFO",
        "message_text": "Test message",
        "state": "RUNNING",
    }
    serializer = LegacyTaskSummaryTaskMessagesFieldsSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

    data = {"unknown_field": "value"}
    serializer = LegacyTaskSummaryTaskMessagesFieldsSerializer(data=data)
    assert not serializer.is_valid()
    assert "unknown_field" in serializer.errors


@pytest.mark.django_db
def test_legacy_task_summary_fields_serializer():
    task_messages_data = [
        {
            "id": datetime.datetime.now().isoformat(),
            "message_type": "INFO",
            "message_text": "Test message",
            "state": "RUNNING",
        }
    ]
    data = {"task_messages": task_messages_data}
    serializer = LegacyTaskSummaryFieldsSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

    data = {"unknown_field": "value"}
    serializer = LegacyTaskSummaryFieldsSerializer(data=data)
    assert not serializer.is_valid()
    assert "unknown_field" in serializer.errors


@pytest.mark.django_db
def test_legacy_task_results_serializer():
    task_messages_data = [
        {
            "id": datetime.datetime.now().isoformat(),
            "message_type": "INFO",
            "message_text": "Test message",
            "state": "RUNNING",
        }
    ]
    summary_fields_data = {"task_messages": task_messages_data}
    data = {
        "state": "RUNNING",
        "id": 123,
        "summary_fields": summary_fields_data,
    }
    serializer = LegacyTaskResultsSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

    data = {"unknown_field": "value"}
    serializer = LegacyTaskResultsSerializer(data=data)
    assert not serializer.is_valid()
    assert "unknown_field" in serializer.errors


@pytest.mark.django_db
def test_legacy_task_detail_serializer():
    task_messages_data = [
        {
            "id": datetime.datetime.now().isoformat(),
            "message_type": "INFO",
            "message_text": "Test message",
            "state": "RUNNING",
        }
    ]
    summary_fields_data = {"task_messages": task_messages_data}
    results_data = {
        "state": "RUNNING",
        "id": 123,
        "summary_fields": summary_fields_data,
    }
    data = {"results": results_data}
    serializer = LegacyTaskDetailSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data == data

    data = {"unknown_field": "value"}
    serializer = LegacyTaskDetailSerializer(data=data)
    assert not serializer.is_valid()
    assert "unknown_field" in serializer.errors


@pytest.mark.django_db
def test_legacy_role_import_detail_serializer():
    task = MagicMock()
    task.pulp_id = "123"
    task.state = "COMPLETED"
    task.enc_kwargs = {
        "request_username": "test_user",
        "github_user": "test_user",
        "github_repo": "test_repo",
        "github_reference": "main",
        "alternate_role_name": "alt_role",
    }
    task.messages = [
        {
            "level": "RUNNING",
            "time": datetime.datetime.now().timestamp(),
            "state": "RUNNING",
            "message": "Test message",
        }
    ]
    role = MagicMock(id=456)
    obj = MagicMock(task=task, role=role, messages=task.messages)

    serializer = LegacyRoleImportDetailSerializer(obj)
    data = serializer.data
    assert data["id"] == uuid_to_int(str(task.pulp_id))
    assert data["pulp_id"] == str(task.pulp_id)
    assert data["role_id"] == role.id
    assert data["state"] == "SUCCESS"
    assert data["summary_fields"] == {
        "request_username": "test_user",
        "github_user": "test_user",
        "github_repo": "test_repo",
        "github_reference": "main",
        "alternate_role_name": "alt_role",
        "task_messages": [
            {
                "id": datetime.datetime.fromtimestamp(
                    task.messages[0]["time"], tz=datetime.timezone.utc
                )
                .replace(tzinfo=None)
                .isoformat(),
                "state": "SUCCESS",
                "message_type": "INFO",
                "message_text": "Test message",
            }
        ],
    }


@pytest.mark.django_db
def test_legacy_role_tag_serializer(legacy_role_tag):
    serializer = LegacyRoleTagSerializer(legacy_role_tag)
    data = serializer.data
    assert data["name"] == legacy_role_tag.name
    assert data["count"] == legacy_role_tag.count
```

This test file covers all the serializers provided in the `galaxy_ng/app/api/v