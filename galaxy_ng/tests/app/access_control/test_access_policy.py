import sys

# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import pytest
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth.models import User, Group, Permission
from django.db.models import Q
from django.conf import settings
from rest_framework.exceptions import NotFound, ValidationError
from pulpcore.plugin.models import UserRole, GroupRole
from pulp_ansible.app.models import AnsibleRepository, AnsibleDistribution, Collection, CollectionVersion
from galaxy_ng.app.models import Namespace, SyncList, LegacyNamespace, LegacyRole
from galaxy_ng.app.access_control.access_policy import (
    AccessPolicyBase,
    AIDenyIndexAccessPolicy,
    AppRootAccessPolicy,
    NamespaceAccessPolicy,
    CollectionAccessPolicy,
    CollectionRemoteAccessPolicy,
    UserAccessPolicy,
    MyUserAccessPolicy,
    SyncListAccessPolicy,
    MySyncListAccessPolicy,
    TagsAccessPolicy,
    TaskAccessPolicy,
    LoginAccessPolicy,
    LogoutAccessPolicy,
    TokenAccessPolicy,
    GroupAccessPolicy,
    DistributionAccessPolicy,
    MyDistributionAccessPolicy,
    ContainerRepositoryAccessPolicy,
    ContainerReadmeAccessPolicy,
    ContainerRegistryRemoteAccessPolicy,
    ContainerRemoteAccessPolicy,
    LandingPageAccessPolicy,
    LegacyAccessPolicy,
    GALAXY_STATEMENTS,
    has_model_or_object_permissions,
    get_view_urlpattern,
    MockPulpAccessPolicy,
)


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="testpass")


@pytest.fixture
def admin_user():
    admin = User.objects.create_user(username="admin", password="adminpass", is_superuser=True)
    return admin


@pytest.fixture
def group():
    return Group.objects.create(name="testgroup")


@pytest.fixture
def permission():
    return Permission.objects.create(codename="test_perm", name="Test Permission", content_type_id=1)


@pytest.fixture
def ansible_repo():
    return AnsibleRepository.objects.create(name="test_repo")


@pytest.fixture
def ansible_distribution(ansible_repo):
    return AnsibleDistribution.objects.create(name="test_dist", base_path="test_base_path", repository=ansible_repo)


@pytest.fixture
def collection(ansible_repo):
    return Collection.objects.create(namespace="test_namespace", name="test_collection", repository=ansible_repo)


@pytest.fixture
def collection_version(collection):
    return CollectionVersion.objects.create(collection=collection, version="1.0.0")


@pytest.fixture
def namespace():
    return Namespace.objects.create(name="test_namespace")


@pytest.fixture
def legacy_namespace():
    return LegacyNamespace.objects.create(name="test_legacy_namespace")


@pytest.fixture
def legacy_role(legacy_namespace):
    return LegacyRole.objects.create(namespace=legacy_namespace, name="test_role")


@pytest.fixture
def sync_list():
    return SyncList.objects.create(name="test_sync_list")


@pytest.fixture
def view():
    mock_view = Mock()
    mock_view.request = Mock()
    mock_view.kwargs = {}
    mock_view.action = "list"
    return mock_view


@pytest.fixture
def request(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.auth = {}
    return mock_request


@pytest.fixture
def request_with_auth(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.auth = {"rh_identity": {"entitlements": {"required_entitlement": {"is_entitled": True}}}}
    return mock_request


@pytest.fixture
def request_with_superuser(admin_user):
    mock_request = Mock()
    mock_request.user = admin_user
    mock_request.auth = {}
    return mock_request


@pytest.fixture
def request_with_github_auth(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/imports/"}
    mock_request.data = {"github_user": user.username}
    return mock_request


@pytest.fixture
def request_with_namespace_owner(user, namespace):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/namespaces/"}
    mock_request.parser_context = {"kwargs": {"pk": namespace.pk}}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_role(user, legacy_role):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/roles/"}
    mock_request.parser_context = {"kwargs": {"id": legacy_role.pk}}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_ai_deny_index(user, legacy_namespace):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {"reference": legacy_namespace.name}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_ai_deny_index_role(user, legacy_role):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {"reference": legacy_role.namespace.name}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_ai_deny_index_user(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {"reference": user.username}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_ai_deny_index_no_user():
    mock_request = Mock()
    mock_request.user = Mock(username="other_user")
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {"reference": "test_user"}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_namespace(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/namespaces/"}
    mock_request.parser_context = {"kwargs": {"pk": 9999}}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_role(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/roles/"}
    mock_request.parser_context = {"kwargs": {"id": 9999}}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_ai_deny_index(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {"reference": "nonexistent_namespace"}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_ai_deny_index_role(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {"reference": "nonexistent_role_namespace"}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_ai_deny_index_user(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {"reference": "nonexistent_user"}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_ai_deny_index_no_user():
    mock_request = Mock()
    mock_request.user = Mock(username="other_user")
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {"reference": "nonexistent_user"}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_ai_deny_index_no_reference(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_ai_deny_index_no_reference_role(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_ai_deny_index_no_reference_user(user):
    mock_request = Mock()
    mock_request.user = user
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_ai_deny_index_no_reference_no_user():
    mock_request = Mock()
    mock_request.user = Mock(username="other_user")
    mock_request.META = {"PATH_INFO": "/ai_deny_index/"}
    mock_request.data = {}
    return mock_request


@pytest.fixture
def request_with_namespace_owner_no_ai_deny_index_no_reference_no_user_no_data(user):
    mock_request = Mock()
    mock_request.user = Mock(username="other_user")
    mock