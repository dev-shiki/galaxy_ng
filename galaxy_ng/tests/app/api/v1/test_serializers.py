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
from galaxy_ng.app.api.v1.serializers import LegacyNamespacesSerializer, LegacyNamespaceOwnerSerializer, LegacyNamespaceProviderSerializer, LegacyUserSerializer, LegacyRoleSerializer, LegacyRoleRepositoryUpdateSerializer, LegacyRoleUpdateSerializer, LegacyRoleContentSerializer, LegacyRoleVersionSummary, LegacyRoleVersionDetail, LegacyRoleVersionsSerializer, LegacyTaskSerializer, LegacySyncSerializer, LegacyImportSerializer, LegacyImportListSerializer, LegacySyncTaskResponseSerializer, LegacyTaskQuerySerializer, LegacyTaskSummaryTaskMessagesFieldsSerializer, LegacyTaskSummaryFieldsSerializer, LegacyTaskResultsSerializer, LegacyTaskDetailSerializer, LegacyRoleImportDetailSerializer, LegacyRoleTagSerializer
from galaxy_ng.app.models.auth import User
from galaxy_ng.app.models.namespace import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace, LegacyRole, LegacyRoleTag
from galaxy_ng.app.utils.rbac import get_v3_namespace_owners
from galaxy_ng.app.utils.galaxy import uuid_to_int

@pytest.fixture
def mock_get_v3_namespace_owners():
    with mock.patch('galaxy_ng.app.utils.rbac.get_v3_namespace_owners') as mock_get_v3_namespace_owners:
        yield mock_get_v3_namespace_owners

@pytest.fixture
def mock_get_url():
    with mock.patch('pulpcore.plugin.util.get_url') as mock_get_url:
        yield mock_get_url

@pytest.fixture
def mock_uuid_to_int():
    with mock.patch('galaxy_ng.app.utils.galaxy.uuid_to_int') as mock_uuid_to_int:
        yield mock_uuid_to_int

@pytest.fixture
def mock_user():
    user = User.objects.create(username='test_user')
    yield user

@pytest.fixture
def mock_namespace():
    namespace = Namespace.objects.create(name='test_namespace')
    yield namespace

@pytest.fixture
def mock_legacy_namespace():
    legacy_namespace = LegacyNamespace.objects.create(name='test_namespace')
    yield legacy_namespace

@pytest.fixture
def mock_legacy_role():
    legacy_role = LegacyRole.objects.create(name='test_role')
    yield legacy_role

@pytest.fixture
def mock_legacy_role_tag():
    legacy_role_tag = LegacyRoleTag.objects.create(name='test_role_tag')
    yield legacy_role_tag

class TestLegacyNamespacesSerializer:
    def test_get_related(self, mock_get_v3_namespace_owners, mock_legacy_namespace):
        serializer = LegacyNamespacesSerializer(mock_legacy_namespace)
        mock_get_v3_namespace_owners.return_value = [mock_user]
        result = serializer.get_related(mock_legacy_namespace)
        assert result == {
            'provider_namespaces': None,
            'content': None,
            'owners': f'/api/v1/namespaces/{mock_legacy_namespace.id}/owners/',
        }

    def test_get_name(self, mock_legacy_namespace):
        serializer = LegacyNamespacesSerializer(mock_legacy_namespace)
        result = serializer.get_name(mock_legacy_namespace)
        assert result == mock_legacy_namespace.name

    def test_get_url(self, mock_legacy_namespace):
        serializer = LegacyNamespacesSerializer(mock_legacy_namespace)
        result = serializer.get_url(mock_legacy_namespace)
        assert result == ''

    def test_get_date_joined(self, mock_legacy_namespace):
        serializer = LegacyNamespacesSerializer(mock_legacy_namespace)
        result = serializer.get_date_joined(mock_legacy_namespace)
        assert result == mock_legacy_namespace.created

    def test_get_summary_fields(self, mock_get_v3_namespace_owners, mock_legacy_namespace, mock_namespace):
        serializer = LegacyNamespacesSerializer(mock_legacy_namespace)
        mock_get_v3_namespace_owners.return_value = [mock_user]
        result = serializer.get_summary_fields(mock_legacy_namespace)
        assert result == {
            'owners': [{'id': mock_user.id, 'username': mock_user.username}],
            'provider_namespaces': [
                {
                    'id': mock_namespace.id,
                    'name': mock_namespace.name,
                    'pulp_href': 'pulp_href',
                }
            ],
        }

    def test_get_avatar_url(self, mock_legacy_namespace):
        serializer = LegacyNamespacesSerializer(mock_legacy_namespace)
        result = serializer.get_avatar_url(mock_legacy_namespace)
        assert result == 'https://github.com/test_namespace.png'

class TestLegacyNamespaceOwnerSerializer:
    def test_get_id(self, mock_user):
        serializer = LegacyNamespaceOwnerSerializer(mock_user)
        result = serializer.get_id(mock_user)
        assert result == mock_user.id

class TestLegacyNamespaceProviderSerializer:
    def test_get_pulp_href(self, mock_namespace):
        serializer = LegacyNamespaceProviderSerializer(mock_namespace)
        result = serializer.get_pulp_href(mock_namespace)
        assert result == 'pulp_href'

class TestLegacyUserSerializer:
    def test_get_username(self, mock_user):
        serializer = LegacyUserSerializer(mock_user)
        result = serializer.get_username(mock_user)
        assert result == mock_user.username

    def test_get_url(self, mock_user):
        serializer = LegacyUserSerializer(mock_user)
        result = serializer.get_url(mock_user)
        assert result == ''

    def test_get_full_name(self, mock_user):
        serializer = LegacyUserSerializer(mock_user)
        result = serializer.get_full_name(mock_user)
        assert result == ''

    def test_get_created(self, mock_user):
        serializer = LegacyUserSerializer(mock_user)
        result = serializer.get_created(mock_user)
        assert result == mock_user.date_joined

    def test_get_date_joined(self, mock_user):
        serializer = LegacyUserSerializer(mock_user)
        result = serializer.get_date_joined(mock_user)
        assert result == mock_user.date_joined

    def test_get_summary_fields(self, mock_user):
        serializer = LegacyUserSerializer(mock_user)
        result = serializer.get_summary_fields(mock_user)
        assert result == {}

    def test_get_avatar_url(self, mock_user):
        serializer = LegacyUserSerializer(mock_user)
        result = serializer.get_avatar_url(mock_user)
        assert result == 'https://github.com/test_user.png'

    def test_get_github_id(self, mock_user):
        serializer = LegacyUserSerializer(mock_user)
        result = serializer.get_github_id(mock_user)
        assert result == None

class TestLegacyRoleSerializer:
    def test_get_id(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_id(mock_legacy_role)
        assert result == mock_legacy_role.pulp_id

    def test_get_upstream_id(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_upstream_id(mock_legacy_role)
        assert result == None

    def test_get_url(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_url(mock_legacy_role)
        assert result == None

    def test_get_created(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_created(mock_legacy_role)
        assert result == mock_legacy_role.date_joined

    def test_get_modified(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_modified(mock_legacy_role)
        assert result == mock_legacy_role.pulp_created

    def test_get_imported(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_imported(mock_legacy_role)
        assert result == None

    def test_get_github_user(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_github_user(mock_legacy_role)
        assert result == mock_legacy_role.namespace.name

    def test_get_username(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_username(mock_legacy_role)
        assert result == mock_legacy_role.namespace.name

    def test_get_github_repo(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_github_repo(mock_legacy_role)
        assert result == None

    def test_get_github_branch(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_github_branch(mock_legacy_role)
        assert result == None

    def test_get_commit(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_commit(mock_legacy_role)
        assert result == None

    def test_get_commit_message(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_commit_message(mock_legacy_role)
        assert result == None

    def test_get_description(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_description(mock_legacy_role)
        assert result == None

    def test_get_summary_fields(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_summary_fields(mock_legacy_role)
        assert result == {
            'dependencies': [],
            'namespace': {
                'id': mock_legacy_role.namespace.id,
                'name': mock_legacy_role.namespace.name,
                'avatar_url': 'https://github.com/test_namespace.png'
            },
            'provider_namespace': None,
            'repository': {},
            'tags': [],
            'versions': []
        }

    def test_get_download_count(self, mock_legacy_role):
        serializer = LegacyRoleSerializer(mock_legacy_role)
        result = serializer.get_download_count(mock_legacy_role)
        assert result == 0

class TestLegacyRoleRepositoryUpdateSerializer:
    def test_is_valid(self):
        serializer = LegacyRoleRepositoryUpdateSerializer({'name': 'test_name'})
        assert serializer.is_valid() == True

    def test_is_valid_with_extra_fields(self):
        serializer = LegacyRoleRepositoryUpdateSerializer({'name': 'test_name', 'extra_field': 'test_value'})
        assert serializer.is_valid() == False

class TestLegacyRoleUpdateSerializer:
    def test_is_valid(self):
        serializer = LegacyRoleUpdateSerializer({'github_user': 'test_user'})
        assert serializer.is_valid() == True

    def test_is_valid_with_extra_fields(self):
        serializer = LegacyRoleUpdateSerializer({'github_user': 'test_user', 'extra_field': 'test_value'})
        assert serializer.is_valid() == False

class TestLegacyRoleContentSerializer:
    def test_get_readme(self, mock_legacy_role):
        serializer = LegacyRoleContentSerializer(mock_legacy_role)
        result = serializer.get_readme(mock_legacy_role)
        assert result == None

    def test_get_readme_html(self, mock_legacy_role):
        serializer = LegacyRoleContentSerializer(mock_legacy_role)
        result = serializer.get_readme_html(mock_legacy_role)
        assert result == None

class TestLegacyRoleVersionSummary:
    def test_to_json(self, mock_legacy_role, mock_legacy_role_version):
        serializer = LegacyRoleVersionSummary(mock_legacy_role, mock_legacy_role_version)
        result = serializer.to_json()
        assert result == {
            'id': mock_legacy_role_version.id,
            'name': mock_legacy_role_version.tag,
            'release_date': mock_legacy_role_version.commit_date
        }

class TestLegacyRoleVersionDetail:
    def test_to_json(self, mock_legacy_role, mock_legacy_role_version):
        serializer = LegacyRoleVersionDetail(mock_legacy_role, mock_legacy_role_version)
        result = serializer.to_json()
        assert result == {
            'id': mock_legacy_role_version.id,
            'name': mock_legacy_role_version.tag,
            'version': mock_legacy_role_version.version,
            'created': mock_legacy_role_version.created,
            'modified': mock_legacy_role_version.modified,
            'commit_date': mock_legacy_role_version.commit_date,
            'commit_sha': mock_legacy_role_version.commit_sha,
            'download_url': 'https://github.com/test_user/test_repo/archive/test_tag.tar.gz'
        }

class TestLegacyRoleVersionsSerializer:
    def test_get_count(self, mock_legacy_role):
        serializer = LegacyRoleVersionsSerializer(mock_legacy_role)
        result = serializer.get_count(mock_legacy_role)
        assert result == 0

    def test_get_next(self, mock_legacy_role):
        serializer = LegacyRoleVersionsSerializer(mock_legacy_role)
        result = serializer.get_next(mock_legacy_role)
        assert result == None

    def test_get_next_link(self, mock_legacy_role):
        serializer = LegacyRoleVersionsSerializer(mock_legacy_role)
        result = serializer.get_next_link(mock_legacy_role)
        assert result == None

    def test_get_previous(self, mock_legacy_role):
        serializer = LegacyRoleVersionsSerializer(mock_legacy_role)
        result = serializer.get_previous(mock_legacy_role)
        assert result == None

    def test_get_previous_link(self, mock_legacy_role):
        serializer = LegacyRoleVersionsSerializer(mock_legacy_role)
        result = serializer.get_previous_link(mock_legacy_role)
        assert result == None

    def test_get_results(self, mock_legacy_role):
        serializer = LegacyRoleVersionsSerializer(mock_legacy_role)
        result = serializer.get_results(mock_legacy_role)
        assert result == []

class TestLegacyTaskSerializer:
    def test_data(self):
        serializer = LegacyTaskSerializer()
        result = serializer.data
        assert result == {}

class TestLegacySyncSerializer:
    def test_is_valid(self):
        serializer = LegacySyncSerializer({'baseurl': 'test_baseurl'})
        assert serializer.is_valid() == True

    def test_is_valid_with_extra_fields(self):
