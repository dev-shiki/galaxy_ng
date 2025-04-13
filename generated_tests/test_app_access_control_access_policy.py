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
    MockPulpAccessPolicy,
    get_view_urlpattern,
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
    namespace = Namespace.objects.create(name="test_namespace")
    return Collection.objects.create(namespace=namespace, repository=ansible_repo)


@pytest.fixture
def collection_version(collection):
    return CollectionVersion.objects.create(collection=collection, version="1.0.0")


@pytest.fixture
def sync_list():
    return SyncList.objects.create(name="test_sync_list")


@pytest.fixture
def legacy_namespace():
    return LegacyNamespace.objects.create(name="test_legacy_namespace")


@pytest.fixture
def legacy_role(legacy_namespace):
    return LegacyRole.objects.create(name="test_legacy_role", namespace=legacy_namespace)


@pytest.fixture
def mock_request(user):
    request = MagicMock()
    request.user = user
    request.auth = {}
    request.data = {}
    request.query_params = {}
    request.META = {'PATH_INFO': '/test/'}
    return request


@pytest.fixture
def mock_view(mock_request):
    view = MagicMock()
    view.request = mock_request
    view.kwargs = {}
    view.action = "list"
    view.get_object = MagicMock(return_value=MagicMock())
    view.get_parent_object = MagicMock(return_value=MagicMock())
    view._get_data = MagicMock(return_value={})
    view._get_path = MagicMock(return_value="test_base_path")
    view.get_repository = MagicMock(return_value=MagicMock())
    return view


@pytest.fixture
def mock_access_policy():
    return AccessPolicyBase()


@pytest.mark.django_db
def test_get_view_urlpattern(mock_view):
    mock_view.parent_viewset = MagicMock(urlpattern=MagicMock(return_value="parent/"))
    mock_view.urlpattern = MagicMock(return_value="child/")
    assert get_view_urlpattern(mock_view) == "parent/child/"

    mock_view.parent_viewset = None
    assert get_view_urlpattern(mock_view) == "child/"


@pytest.mark.django_db
def test_has_model_or_object_permissions(user, permission):
    user.user_permissions.add(permission)
    assert has_model_or_object_permissions(user, "test_perm")

    obj = MagicMock()
    obj.has_perm = MagicMock(return_value=True)
    assert has_model_or_object_permissions(user, "test_perm", obj)

    obj.has_perm.return_value = False
    assert not has_model_or_object_permissions(user, "test_perm", obj)


@pytest.mark.django_db
def test_mock_pulp_access_policy():
    mock_policy = MockPulpAccessPolicy({"statements": [{"action": "*", "principal": "admin", "effect": "allow"}]})
    assert mock_policy.statements == [{"action": "*", "principal": "admin", "effect": "allow"}]


@pytest.mark.django_db
def test_galaxy_statements():
    statements = GalaxyStatements()
    assert statements.galaxy_statements is not None
    assert "insights" in statements.galaxy_statements
    assert "standalone" in statements.galaxy_statements


@pytest.mark.django_db
def test_get_pulp_access_policy():
    statements = GalaxyStatements()
    policy = statements.get_pulp_access_policy("nonexistent")
    assert policy is None

    policy = statements.get_pulp_access_policy("nonexistent", default={"statements": []})
    assert policy.statements == []


@pytest.mark.django_db
def test_access_policy_base_get_access_policy(mock_view):
    policy = AccessPolicyBase.get_access_policy(mock_view)
    assert policy.statements == [{"action": "*", "principal": "admin", "effect": "allow"}]

    mock_view.DEFAULT_ACCESS_POLICY = {"statements": [{"action": "test", "principal": "user", "effect": "allow"}]}
    policy = AccessPolicyBase.get_access_policy(mock_view)
    assert policy.statements == [{"action": "test", "principal": "user", "effect": "allow"}]


@pytest.mark.django_db
def test_access_policy_base_scope_by_view_repository_permissions(mock_view, user, ansible_repo, permission):
    mock_view.request.user = user
    qs = AnsibleRepository.objects.all()
    scoped_qs = AccessPolicyBase().scope_by_view_repository_permissions(mock_view, qs)
    assert scoped_qs.count() == 0

    user.user_permissions.add(permission)
    scoped_qs = AccessPolicyBase().scope_by_view_repository_permissions(mock_view, qs)
    assert scoped_qs.count() == 1


@pytest.mark.django_db
def test_access_policy_base_scope_synclist_distributions(mock_view, user, sync_list, permission):
    mock_view.request.user = user
    qs = sync_list.distributions.all()
    scoped_qs = AccessPolicyBase().scope_synclist_distributions(mock_view, qs)
    assert scoped_qs.count() == 0

    user.user_permissions.add(permission)
    scoped_qs = AccessPolicyBase().scope_synclist_distributions(mock_view, qs)
    assert scoped_qs.count() == 0


@pytest.mark.django_db
def test_access_policy_base_scope_queryset(mock_view, user, ansible_repo, permission):
    mock_view.request.user = user
    qs = AnsibleRepository.objects.all()
    scoped_qs = AccessPolicyBase().scope_queryset(mock_view, qs)
    assert scoped_qs.count() == 0

    mock_view.action = "list"
    mock_view.DEFAULT_ACCESS_POLICY = {"queryset_scoping": {"function": "scope_by_view_repository_permissions"}}
    scoped_qs = AccessPolicyBase().scope_queryset(mock_view, qs)
    assert scoped_qs.count() == 0

    user.user_permissions.add(permission)
    scoped_qs = AccessPolicyBase().scope_queryset(mock_view, qs)
    assert scoped_qs.count() == 1


@pytest.mark.django_db
def test_access_policy_base_v3_can_view_repo_content(mock_view, user, ansible_distribution, permission):
    mock_view.kwargs = {"distro_base_path": "test_base_path"}
    mock_view.request.user = user
    assert not AccessPolicyBase().v3_can_view_repo_content(mock_view.request, mock_view, "list")

    user.user_permissions.add(permission)
    assert AccessPolicyBase().v3_can_view_repo_content(mock_view.request, mock_view, "list")


@pytest.mark.django_db
def test_access_policy_base_v3_can_destroy_collections(mock_view, user, collection, permission):
    mock_view.request.user = user
    mock_view.get_object = MagicMock(return_value=collection)
    assert not AccessPolicyBase().v3_can_destroy_collections(mock_view.request, mock_view, "destroy")

    user.user_permissions.add(permission)
    assert AccessPolicyBase().v3_can_destroy_collections(mock_view.request, mock_view, "destroy")


@pytest.mark.django_db
def test_access_policy_base_v3_can_view_users(mock_view, user):
    mock_view.request.user = user
    assert not AccessPolicyBase().v3_can_view_users(mock_view.request, mock_view, "list")

