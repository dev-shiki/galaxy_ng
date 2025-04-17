import os
import sys
import re
import pytest
from unittest import mock
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.utils import rbac
from galaxy_ng.social import __init__ as social_module
from galaxy_ng.social import factories as social_factories

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

# Mock settings
settings.SOCIAL_AUTH_GITHUB_KEY = 'mock_key'
settings.SOCIAL_AUTH_GITHUB_SECRET = 'mock_secret'
settings.SOCIAL_AUTH_GITHUB_API_URL = 'https://api.github.com'
settings.SOCIAL_AUTH_GITHUB_BASE_URL = 'https://github.com'

# Mock requests
requests_mock = mock.Mock()
requests_mock.post.return_value.json.return_value = {'access_token': 'mock_token'}
requests_mock.get.return_value.json.return_value = {'login': 'mock_login', 'email': 'mock_email'}

# Mock rbac
rbac.get_v3_namespace_owners = mock.Mock(return_value=['mock_user'])
rbac.get_owned_v3_namespaces = mock.Mock(return_value=['mock_namespace'])

# Mock Namespace and LegacyNamespace
Namespace.objects.get_or_create.return_value = (mock.Mock(), True)
LegacyNamespace.objects.get_or_create.return_value = (mock.Mock(), True)

# Mock social module
social_module.GITHUB_ACCOUNT_SCOPE = 'github'
social_module.logger = mock.Mock()

# Fixtures
@pytest.fixture
def mock_github_user():
    return {'login': 'mock_login', 'email': 'mock_email'}

@pytest.fixture
def mock_github_access_token():
    return 'mock_token'

@pytest.fixture
def mock_github_code():
    return 'mock_code'

@pytest.fixture
def mock_request():
    return mock.Mock()

# Tests
class TestGalaxyNGOAuth2:
    def test_get_session_state(self):
        social_module.GalaxyNGOAuth2().get_session_state()
        social_module.logger.debug.assert_called_once()

    def test_do_auth(self, mock_github_user, mock_github_access_token, mock_request):
        social_module.GalaxyNGOAuth2().do_auth(mock_github_access_token, mock_request)
        social_module.logger.debug.assert_called_twice()

    def test_handle_v3_namespace(self, mock_github_user):
        social_module.GalaxyNGOAuth2().handle_v3_namespace(mock_github_user, 'mock_email', 'mock_login', 'mock_id')
        social_module.logger.info.assert_called()

    def test_generate_available_namespace_name(self):
        social_module.GalaxyNGOAuth2().generate_available_namespace_name('mock_login', 'mock_id')
        social_module.logger.info.assert_called()

    def test_validate_namespace_name(self):
        assert social_module.GalaxyNGOAuth2().validate_namespace_name('mock_name')
        assert not social_module.GalaxyNGOAuth2().validate_namespace_name('')

    def test_transform_namespace_name(self):
        assert social_module.GalaxyNGOAuth2().transform_namespace_name('mock_name') == 'mock_name'

    def test__ensure_namespace(self):
        social_module.GalaxyNGOAuth2()._ensure_namespace('mock_name', 'mock_user')
        social_module.logger.info.assert_called()

    def test__ensure_legacynamespace(self):
        social_module.GalaxyNGOAuth2()._ensure_legacynamespace('mock_login', 'mock_namespace')
        social_module.logger.info.assert_called()

    def test_get_github_access_token(self, mock_github_code):
        social_module.GalaxyNGOAuth2().get_github_access_token(mock_github_code)
        requests_mock.post.assert_called_once()

    def test_get_github_user(self, mock_github_access_token):
        social_module.GalaxyNGOAuth2().get_github_user(mock_github_access_token)
        requests_mock.get.assert_called_once()

    def test_auth_complete(self, mock_request):
        social_module.GalaxyNGOAuth2().auth_complete(mock_request)
        social_module.logger.debug.assert_called()

class TestGalaxyNGOAuth2ErrorHandling:
    def test_get_session_state_error(self):
        social_module.GalaxyNGOAuth2().get_session_state()
        social_module.logger.error.assert_called_once()

    def test_do_auth_error(self, mock_github_user, mock_github_access_token, mock_request):
        social_module.GalaxyNGOAuth2().do_auth(mock_github_access_token, mock_request)
        social_module.logger.error.assert_called()

    def test_handle_v3_namespace_error(self, mock_github_user):
        social_module.GalaxyNGOAuth2().handle_v3_namespace(mock_github_user, 'mock_email', 'mock_login', 'mock_id')
        social_module.logger.error.assert_called()

    def test_generate_available_namespace_name_error(self):
        social_module.GalaxyNGOAuth2().generate_available_namespace_name('mock_login', 'mock_id')
        social_module.logger.error.assert_called()

    def test_validate_namespace_name_error(self):
        assert not social_module.GalaxyNGOAuth2().validate_namespace_name('')

    def test_transform_namespace_name_error(self):
        assert social_module.GalaxyNGOAuth2().transform_namespace_name('') == ''

    def test__ensure_namespace_error(self):
        social_module.GalaxyNGOAuth2()._ensure_namespace('mock_name', 'mock_user')
        social_module.logger.error.assert_called()

    def test__ensure_legacynamespace_error(self):
        social_module.GalaxyNGOAuth2()._ensure_legacynamespace('mock_login', 'mock_namespace')
        social_module.logger.error.assert_called()

    def test_get_github_access_token_error(self, mock_github_code):
        social_module.GalaxyNGOAuth2().get_github_access_token(mock_github_code)
        requests_mock.post.assert_called_once()

    def test_get_github_user_error(self, mock_github_access_token):
        social_module.GalaxyNGOAuth2().get_github_user(mock_github_access_token)
        requests_mock.get.assert_called_once()

    def test_auth_complete_error(self, mock_request):
        social_module.GalaxyNGOAuth2().auth_complete(mock_request)
        social_module.logger.error.assert_called()
