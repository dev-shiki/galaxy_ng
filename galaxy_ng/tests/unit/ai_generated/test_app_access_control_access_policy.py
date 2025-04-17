import os
import sys
import re
import pytest
from unittest import mock

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.access_control.statements import PULP_VIEWSETS
from galaxy_ng.app.constants import COMMUNITY_DOMAINS
from galaxy_ng.app.utils.rbac import get_v3_namespace_owners
from pulpcore.plugin.util import extract_pk
from pulp_ansible.app import models as ansible_models
from pulp_container.app import models as container_models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Q, Exists, OuterRef, CharField
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _

# Fixtures
@pytest.fixture
def mock_pulp_access_policy():
    return mock.MagicMock()

@pytest.fixture
def mock_galaxy_statements():
    return mock.MagicMock()

@pytest.fixture
def mock_request():
    return mock.MagicMock()

@pytest.fixture
def mock_view():
    return mock.MagicMock()

@pytest.fixture
def mock_user():
    return get_user_model().objects.create_user('testuser', 'testuser@example.com', 'password')

@pytest.fixture
def mock_namespace():
    return models.Namespace.objects.create(name='testnamespace')

@pytest.fixture
def mock_legacy_namespace():
    return models.LegacyNamespace.objects.create(name='testlegacynamespace')

@pytest.fixture
def mock_collection():
    return models.Collection.objects.create(namespace=mock_namespace)

@pytest.fixture
def mock_collection_remote():
    return models.CollectionRemote.objects.create(namespace=mock_namespace)

@pytest.fixture
def mock_distribution():
    return models.Distribution.objects.create(namespace=mock_namespace)

@pytest.fixture
def mock_container_distribution():
    return container_models.ContainerDistribution.objects.create(namespace=mock_namespace)

@pytest.fixture
def mock_container_push_repository():
    return container_models.ContainerPushRepository.objects.create(namespace=mock_namespace)

@pytest.fixture
def mock_container_push_repository_version():
    return container_models.PushRepositoryVersion.objects.create(repository=mock_container_push_repository)

# Test classes and functions
class TestAccessPolicyBase:
    def test_get_access_policy(self, mock_pulp_access_policy, mock_galaxy_statements):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.get_access_policy(mock_view)
        mock_galaxy_statements.get_pulp_access_policy.assert_called_once_with('AppRootViewSet', default=[])

    def test_scope_by_view_repository_permissions(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.scope_by_view_repository_permissions(mock_view, models.Repository.objects.all(), field_name="repository")
        mock_request.user.has_perm.assert_called_once_with('ansible.view_ansiblerepository')

    def test_scope_synclist_distributions(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.scope_synclist_distributions(mock_view, models.SyncList.objects.all())
        mock_request.user.has_perm.assert_called_once_with('galaxy.view_synclist')

    def test_scope_queryset(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.scope_queryset(mock_view, models.Repository.objects.all())
        mock_request.user.has_perm.assert_called_once_with('ansible.view_ansiblerepository')

    def test_v3_can_view_repo_content(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.v3_can_view_repo_content(mock_request, mock_view, 'list')
        mock_request.user.has_perm.assert_called_once_with('ansible.view_ansiblerepository')

    def test_v3_can_destroy_collections(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.v3_can_destroy_collections(mock_request, mock_view, 'destroy')
        mock_request.user.has_perm.assert_called_once_with('galaxy.change_namespace')

    def test_v3_can_view_users(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.v3_can_view_users(mock_request, mock_view, 'list')
        mock_request.user.has_perm.assert_called_once_with('galaxy.view_user')

    def test_has_ansible_repo_perms(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.has_ansible_repo_perms(mock_request, mock_view, 'list', 'ansible.view_ansiblerepository')
        mock_request.user.has_perm.assert_called_once_with('ansible.view_ansiblerepository')

    def test_can_copy_or_move(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.can_copy_or_move(mock_request, mock_view, 'copy', 'ansible.view_ansiblerepository')
        mock_request.user.has_perm.assert_called_once_with('ansible.view_ansiblerepository')

    def test_can_sign_collections(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.can_sign_collections(mock_request, mock_view, 'sign')
        mock_request.user.has_perm.assert_called_once_with('ansible.modify_ansible_repo_content')

    def test_unauthenticated_collection_download_enabled(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.unauthenticated_collection_download_enabled(mock_request, mock_view, 'download')
        mock_request.user.has_perm.assert_called_once_with('galaxy.view_user')

    def test_unauthenticated_collection_access_enabled(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.unauthenticated_collection_access_enabled(mock_request, mock_view, 'list')
        mock_request.user.has_perm.assert_called_once_with('galaxy.view_user')

    def test_has_concrete_perms(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.has_concrete_perms(mock_request, mock_view, 'list', 'ansible.view_ansiblerepository')
        mock_request.user.has_perm.assert_called_once_with('ansible.view_ansiblerepository')

    def test_signatures_not_required_for_repo(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.signatures_not_required_for_repo(mock_request, mock_view, 'create')
        mock_request.user.has_perm.assert_called_once_with('ansible.modify_ansible_repo_content')

    def test_is_not_protected_base_path(self, mock_request, mock_view, mock_namespace):
        access_policy_base = access_policy.AccessPolicyBase()
        access_policy_base.is_not_protected_base_path(mock_request, mock_view,