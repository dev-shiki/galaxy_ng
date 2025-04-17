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
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from galaxy_ng.app import models
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.access_control.statements import PULP_VIEWSETS
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
)

User = get_user_model()

@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", email="testuser@example.com", password="password")

@pytest.fixture
def admin_user():
    return User.objects.create_superuser(username="adminuser", email="adminuser@example.com", password="password")

@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def access_policy_base():
    return AccessPolicyBase()

@pytest.fixture
def access_policy():
    return AIDenyIndexAccessPolicy()

class TestAccessPolicyBase(TestCase):
    def test_get_access_policy(self):
        view = mock.Mock()
        view.parent_viewset = None
        view.urlpattern = lambda: "test_urlpattern"
        access_policy = access_policy_base.get_access_policy(view)
        self.assertEqual(access_policy.statements, [])

    def test_get_access_policy_with_custom_policy(self):
        view = Mock()
        view.parent_viewset = None
        view.urlpattern = lambda: "test_urlpattern"
        PULP_VIEWSETS["test_urlpattern"] = [{"action": "*", "principal": "admin", "effect": "allow"}]
        access_policy = access_policy_base.get_access_policy(view)
        self.assertEqual(access_policy.statements, [{"action": "*", "principal": "admin", "effect": "allow"}])

    def test_scope_by_view_repository_permissions(self):
        view = Mock()
        view.request.user = user
        view.request.user.has_perm.return_value = True
        qs = models.Repository.objects.all()
        access_policy = access_policy_base
        result = access_policy.scope_by_view_repository_permissions(view, qs)
        self.assertEqual(result, qs)

    def test_scope_by_view_repository_permissions_with_private_repo(self):
        view = Mock()
        view.request.user = user
        view.request.user.has_perm.return_value = False
        qs = models.Repository.objects.all()
        access_policy = access_policy_base
        result = access_policy.scope_by_view_repository_permissions(view, qs)
        self.assertEqual(result, qs.filter(private=False))

    def test_scope_synclist_distributions(self):
        view = Mock()
        view.request.user = user
        view.request.user.has_perm.return_value = True
        qs = models.SyncList.objects.all()
        access_policy = access_policy_base
        result = access_policy.scope_synclist_distributions(view, qs)
        self.assertEqual(result, qs)

    def test_scope_synclist_distributions_with_private_repo(self):
        view = Mock()
        view.request.user = user
        view.request.user.has_perm.return_value = False
        qs = models.SyncList.objects.all()
        access_policy = access_policy_base
        result = access_policy.scope_synclist_distributions(view, qs)
        self.assertEqual(result, qs.filter(private=False))

class TestAccessPolicy(TestCase):
    def test_can_edit_ai_deny_index(self):
        view = Mock()
        view.get_object.return_value = models.Namespace.objects.create(name="testnamespace")
        access_policy = access_policy
        result = access_policy.can_edit_ai_deny_index(view.request, view, "change_namespace")
        self.assertTrue(result)

    def test_can_edit_ai_deny_index_with_legacy_namespace(self):
        view = Mock()
        view.get_object.return_value = LegacyNamespace.objects.create(name="testnamespace")
        access_policy = access_policy
        result = access_policy.can_edit_ai_deny_index(view.request, view, "change_namespace")
        self.assertTrue(result)

    def test_can_edit_ai_deny_index_without_permission(self):
        view = Mock()
        view.get_object.return_value = models.Namespace.objects.create(name="testnamespace")
        access_policy = access_policy
        view.request.user.has_perm.return_value = False
        result = access_policy.can_edit_ai_deny_index(view.request, view, "change_namespace")
        self.assertFalse(result)

class TestAccessPolicyBaseMethods(TestCase):
    def test_v3_can_view_repo_content(self):
        view = Mock()
        view.kwargs = {"distro_base_path": "test_base_path"}
        access_policy = access_policy_base
        result = access_policy.v3_can_view_repo_content(view.request, view, "list")
        self.assertTrue(result)

    def test_v3_can_view_repo_content_without_permission(self):
        view = Mock()
        view.kwargs = {"distro_base_path": "test_base_path"}
        access_policy = access_policy_base
        view.request.user.has_perm.return_value = False
        result = access_policy.v3_can_view_repo_content(view.request, view, "list")
        self.assertFalse(result)

    def test_v3_can_destroy_collections(self):
        view = Mock()
        view.get_object.return_value = models.Collection.objects.create(namespace="testnamespace")
        access_policy = access_policy_base
        result = access_policy.v3_can_destroy_collections(view.request, view, "destroy")
        self.assertTrue(result)

    def test_v3_can_destroy_collections_without_permission(self):
        view = Mock()
        view.get_object.return_value = models.Collection.objects.create(namespace="testnamespace")
        access_policy = access_policy_base
        view.request.user.has_perm.return_value = False
        result = access_policy.v3_can_destroy_collections(view.request, view, "destroy")
        self.assertFalse(result)

    def test_v3_can_view_users(self):
        view = Mock()
        access_policy = access_policy_base
        result = access_policy.v3_can_view_users(view.request, view, "list")
        self.assertTrue(result)

    def test_v3_can_view_users_without_permission(self):
        view = Mock()
        access_policy = access_policy_base
        view.request.user.has_perm.return_value = False
        result = access_policy