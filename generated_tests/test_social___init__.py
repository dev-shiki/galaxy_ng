import pytest
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from social_core.backends.github import GithubOAuth2
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.utils import rbac
from galaxy_importer.constants import NAME_REGEXP

from galaxy_ng.social import __init__ as social_module

@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def github_backend():
    return GithubOAuth2()

@pytest.fixture
def namespace():
    return Namespace.objects.create(name='test-namespace')

@pytest.fixture
def legacy_namespace():
    return LegacyNamespace.objects.create(name='test-legacy-namespace')

@pytest.fixture
def user():
    return settings.AUTH_USER_MODEL.objects.create(username='test-user')

@pytest.fixture
def v3_namespace():
    return Namespace.objects.create(name='test-v3-namespace')

@pytest.fixture
def v3_namespace_owned_by_user():
    namespace = Namespace.objects.create(name='test-v3-namespace-owned-by-user')
    rbac.add_user_to_v3_namespace(user(), namespace)
    return namespace

@pytest.fixture
def available_namespace_name():
    return 'test-available-namespace-name'

@pytest.fixture
def invalid_namespace_name():
    return 'test-invalid-namespace-name'

class TestSocialModule(TestCase):

    def test_logged_decorator(self):
        def test_func():
            return 'test'
        decorated_func = social_module.logged(test_func)
        self.assertEqual(decorated_func(), 'test')
        self.assertEqual(decorated_func(), 'test')

    def test_get_session_state(self, github_backend):
        request = self.client.get(reverse('social:complete'), {'state': 'test-state'})
        response = github_backend.auth_complete(request)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, settings.SOCIAL_AUTH_GITHUB_BASE_URL + '/login/oauth/authorize?client_id=' + settings.SOCIAL_AUTH_GITHUB_KEY + '&redirect_uri=' + settings.SOCIAL_AUTH_GITHUB_REDIRECT_URI + '&response_type=code&scope=' + settings.SOCIAL_AUTH_GITHUB_SCOPE + '&state=test-state')

    def test_get_github_access_token(self, github_backend):
        code = 'test-code'
        response = github_backend.get_github_access_token(code)
        self.assertEqual(response, 'test-access-token')

    def test_get_github_user(self, github_backend):
        access_token = 'test-access-token'
        response = github_backend.get_github_user(access_token)
        self.assertEqual(response, {'login': 'test-login', 'id': 1, 'email': 'test-email'})

    def test_auth_complete(self, client, github_backend):
        code = 'test-code'
        response = client.get(reverse('social:complete'), {'code': code})
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, settings.SOCIAL_AUTH_GITHUB_BASE_URL + '/login/oauth/access_token?client_id=' + settings.SOCIAL_AUTH_GITHUB_KEY + '&client_secret=' + settings.SOCIAL_AUTH_GITHUB_SECRET + '&redirect_uri=' + settings.SOCIAL_AUTH_GITHUB_REDIRECT_URI + '&code=test-code&grant_type=authorization_code')

    def test_handle_v3_namespace(self, github_backend, namespace, user):
        response = github_backend.handle_v3_namespace(None, None, None, None)
        self.assertEqual(response, (namespace, False))

    def test_handle_v3_namespace_found_namespace(self, github_backend, namespace, user):
        response = github_backend.handle_v3_namespace(None, None, None, None)
        self.assertEqual(response, (namespace, False))

    def test_handle_v3_namespace_owned_namespace(self, github_backend, v3_namespace_owned_by_user, user):
        response = github_backend.handle_v3_namespace(None, None, None, None)
        self.assertEqual(response, (v3_namespace_owned_by_user, False))

    def test_handle_v3_namespace_new_namespace(self, github_backend, available_namespace_name):
        response = github_backend.handle_v3_namespace(None, None, None, None)
        self.assertEqual(response, (Namespace.objects.get(name=available_namespace_name), True))

    def test_handle_v3_namespace_short_circuit(self, github_backend, v3_namespace_owned_by_user, user):
        response = github_backend.handle_v3_namespace(None, None, None, None)
        self.assertEqual(response, (v3_namespace_owned_by_user, False))

    def test_handle_v3_namespace_short_circuit_candidate(self, github_backend, v3_namespace_owned_by_user, user):
        response = github_backend.handle_v3_namespace(None, None, None, None)
        self.assertEqual(response, (v3_namespace_owned_by_user, False))

    def test_handle_v3_namespace_short_circuit_no_candidate(self, github_backend, v3_namespace_owned_by_user, user):
        response = github_backend.handle_v3_namespace(None, None, None, None)
        self.assertEqual(response, (None, False))

    def test_generate_available_namespace_name(self, github_backend, available_namespace_name):
        response = github_backend.generate_available_namespace_name(None, None)
        self.assertEqual(response, available_namespace_name)

    def test_generate_available_namespace_name_counter(self, github_backend):
        response = github_backend.generate_available_namespace_name(None, None)
        self.assertEqual(response, 'test-available-namespace-name0')

    def test_generate_available_namespace_name_counter_increment(self, github_backend):
        response = github_backend.generate_available_namespace_name(None, None)
        self.assertEqual(response, 'test-available-namespace-name1')

    def test_validate_namespace_name(self, github_backend):
        response = github_backend.validate_namespace_name('test-namespace')
        self.assertEqual(response, True)

    def test_validate_namespace_name_invalid(self, github_backend):
        response = github_backend.validate_namespace_name('test-invalid-namespace-name')
        self.assertEqual(response, False)

    def test_transform_namespace_name(self, github_backend):
        response = github_backend.transform_namespace_name('test-namespace')
        self.assertEqual(response, 'test_namespace')

    def test_transform_namespace_name_invalid(self, github_backend):
        response = github_backend.transform_namespace_name('test-namespace')
        self.assertEqual(response, 'test_namespace')

    def test__ensure_namespace(self, github_backend, namespace):
        response = github_backend._ensure_namespace(namespace.name, None)
        self.assertEqual(response, (namespace, False))

    def test__ensure_namespace_created(self, github_backend, namespace):
        response = github_backend._ensure_namespace(namespace.name, None)
        self.assertEqual(response, (namespace, True))

    def test__ensure_legacynamespace(self, github_backend, legacy_namespace):
        response = github_backend._ensure_legacynamespace(None, None)
        self.assertEqual(response, (legacy_namespace, False))

    def test__ensure_legacynamespace_created(self, github_backend, legacy_namespace):
        response = github_backend._ensure_legacynamespace(None, None)
        self.assertEqual(response, (legacy_namespace, True))
