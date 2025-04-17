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
from galaxy_ng.social import __init__ as social
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.utils import rbac
from galaxy_importer.constants import NAME_REGEXP

@pytest.fixture
def mock_settings():
    settings = mock.Mock()
    settings.SOCIAL_AUTH_GITHUB_BASE_URL = 'https://github.com'
    settings.SOCIAL_AUTH_GITHUB_KEY = 'key'
    settings.SOCIAL_AUTH_GITHUB_SECRET = 'secret'
    settings.SOCIAL_AUTH_GITHUB_API_URL = 'https://api.github.com'
    return settings

@pytest.fixture
def mock_request():
    request = mock.Mock()
    request.GET = mock.Mock()
    request.GET.get.return_value = 'code'
    return request

@pytest.fixture
def mock_github_response():
    return mock.Mock(json={'access_token': 'token'})

@pytest.fixture
def mock_github_user():
    return mock.Mock()

@pytest.fixture
def mock_namespace():
    return Namespace.objects.create(name='namespace')

@pytest.fixture
def mock_legacy_namespace():
    return LegacyNamespace.objects.create(name='login')

class TestGalaxyNGOAuth2:
    def test_get_session_state(self, mock_github_response):
        mock_github_response.json.return_value = {'state': 'state'}
        oauth2 = social.GalaxyNGOAuth2()
        return oauth2.get_session_state()

    def test_get_session_state(self, mock_github_response):
        assert self._get_session_state(mock_github_response) == 'state'

    def test_get_session_state_none(self, mock_github_response):
        mock_github_response.json.return_value = None
        oauth2 = social.GalaxyNGOAuth2()
        assert oauth2.get_session_state() is None

    def test_do_auth(self, mock_request, mock_github_response, mock_github_user):
        oauth2 = social.GalaxyNGOAuth2()
        oauth2.get_github_access_token.return_value = 'access_token'
        oauth2.get_github_user.return_value = mock_github_user
        auth_response = oauth2.do_auth('access_token', mock_request)
        assert auth_response is not None

    def test_do_auth_error(self, mock_request, mock_github_response):
        oauth2 = social.GalaxyNGOAuth2()
        oauth2.get_github_access_token.return_value = None
        auth_response = oauth2.do_auth('access_token', mock_request)
        assert auth_response is None

    def test_handle_v3_namespace(self, mock_namespace, mock_request):
        oauth2 = social.GalaxyNGOAuth2()
        oauth2.handle_v3_namespace(mock_request, 'email', 'login', 'github_id')
        assert mock_namespace in oauth2.handle_v3_namespace(mock_request, 'email', 'login', 'github_id')

    def test_handle_v3_namespace_none(self, mock_request):
        oauth2 = social.GalaxyNGOAuth2()
        assert oauth2.handle_v3_namespace(mock_request, 'email', 'login', 'github_id') is None

    def test_generate_available_namespace_name(self):
        oauth2 = social.GalaxyNGOAuth2()
        assert oauth2.generate_available_namespace_name('login', 'github_id') is not None

    def test_validate_namespace_name(self):
        oauth2 = social.GalaxyNGOAuth2()
        assert oauth2.validate_namespace_name('namespace') is True

    def test_validate_namespace_name_error(self):
        oauth2 = social.GalaxyNGOAuth2()
        assert oauth2.validate_namespace_name('error') is False

    def test_transform_namespace_name(self):
        oauth2 = social.GalaxyNGOAuth2()
        assert oauth2.transform_namespace_name('namespace') == 'namespace'

    def test_transform_namespace_name_error(self):
        oauth2 = social.GalaxyNGOAuth2()
        assert oauth2.transform_namespace_name('error') == 'error'

    def test__ensure_namespace(self, mock_namespace):
        oauth2 = social.GalaxyNGOAuth2()
        oauth2._ensure_namespace('namespace', 'user')
        assert mock_namespace in oauth2._ensure_namespace('namespace', 'user')

    def test__ensure_namespace_none(self):
        oauth2 = social.GalaxyNGOAuth2()
        assert oauth2._ensure_namespace('namespace', 'user') is None

    def test__ensure_legacynamespace(self, mock_legacy_namespace):
        oauth2 = social.GalaxyNGOAuth2()
        oauth2._ensure_legacynamespace('login', 'v3_namespace')
        assert mock_legacy_namespace in oauth2._ensure_legacynamespace('login', 'v3_namespace')

    def test__ensure_legacynamespace_none(self):
        oauth2 = social.GalaxyNGOAuth2()
        assert oauth2._ensure_legacynamespace('login', 'v3_namespace') is None

    def test_get_github_access_token(self, mock_request):
        oauth2 = social.GithubOAuth2()
        oauth2.get_github_access_token.return_value = 'access_token'
        assert oauth2.get_github_access_token('code') == 'access_token'

    def test_get_github_access_token_error(self, mock_request):
        oauth2 = social.GithubOAuth2()
        oauth2.get_github_access_token.return_value = None
        assert oauth2.get_github_access_token('code') is None

    def test_get_github_user(self, mock_github_response):
        oauth2 = social.GithubOAuth2()
        oauth2.get_github_user.return_value = mock_github_response
        assert oauth2.get_github_user('access_token') == mock_github_response

    def test_get_github_user_error(self, mock_github_response):
        oauth2 = social.GithubOAuth2()
        oauth2.get_github_user.return_value = None
        assert oauth2.get_github_user('access_token') is None

    def test_auth_complete(self, mock_request, mock_github_response):
        oauth2 = social.GalaxyNGOAuth2()
        oauth2.auth_complete.return_value = 'auth_response'
        assert oauth2.auth_complete(mock_request) == 'auth_response'

    def test_auth_complete_error