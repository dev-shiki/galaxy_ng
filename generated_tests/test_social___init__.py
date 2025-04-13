import pytest
import logging
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User
from social_core.exceptions import AuthFailed
from galaxy_ng.app.models import Namespace, LegacyNamespace
from galaxy_ng.app.utils import rbac
from galaxy_ng.social import GalaxyNGOAuth2
from galaxy_importer.constants import NAME_REGEXP

pytestmark = pytest.mark.django_db

@pytest.fixture
def mock_requests_post():
    with patch('requests.post') as mock:
        yield mock

@pytest.fixture
def mock_requests_get():
    with patch('requests.get') as mock:
        yield mock

@pytest.fixture
def mock_strategy():
    strategy = MagicMock()
    strategy.session_get.return_value = 'state'
    strategy.authenticate.return_value = {'user': User.objects.create_user(username='testuser')}
    return strategy

@pytest.fixture
def mock_backend(mock_strategy):
    backend = GalaxyNGOAuth2(strategy=mock_strategy, redirect_uri='http://example.com')
    return backend

@pytest.fixture
def mock_namespace():
    return Namespace.objects.create(name='testnamespace')

@pytest.fixture
def mock_legacy_namespace(mock_namespace):
    return LegacyNamespace.objects.create(name='testuser', namespace=mock_namespace)

@pytest.fixture
def mock_user():
    return User.objects.create_user(username='testuser')

class TestGalaxyNGOAuth2(TestCase):

    def test_get_session_state(self, mock_backend):
        assert mock_backend.get_session_state() == 'state'

    def test_do_auth(self, mock_backend, mock_user, mock_namespace, mock_legacy_namespace):
        with patch.object(mock_backend, 'get_github_user', return_value={
            'id': 12345,
            'login': 'testuser',
            'email': 'testuser@example.com'
        }):
            with patch.object(mock_backend, 'handle_v3_namespace', return_value=(mock_namespace, False)):
                with patch.object(mock_backend, '_ensure_legacynamespace', return_value=(mock_legacy_namespace, False)):
                    response = mock_backend.do_auth('access_token')
                    assert response['user'] == mock_user

    def test_handle_v3_namespace_new(self, mock_backend, mock_user):
        with patch.object(mock_backend, 'transform_namespace_name', return_value='newnamespace'):
            with patch.object(mock_backend, 'validate_namespace_name', return_value=True):
                with patch.object(mock_backend, '_ensure_namespace', return_value=(Namespace.objects.create(name='newnamespace'), True)):
                    namespace, created = mock_backend.handle_v3_namespace(mock_user, 'test@example.com', 'testuser', 12345)
                    assert namespace.name == 'newnamespace'
                    assert created is True

    def test_handle_v3_namespace_existing(self, mock_backend, mock_user, mock_namespace):
        with patch.object(mock_backend, 'transform_namespace_name', return_value='testnamespace'):
            with patch.object(mock_backend, 'validate_namespace_name', return_value=True):
                namespace, created = mock_backend.handle_v3_namespace(mock_user, 'test@example.com', 'testuser', 12345)
                assert namespace == mock_namespace
                assert created is False

    def test_handle_v3_namespace_invalid_name(self, mock_backend, mock_user):
        with patch.object(mock_backend, 'transform_namespace_name', return_value='invalid__name'):
            with patch.object(mock_backend, 'validate_namespace_name', return_value=False):
                namespace, created = mock_backend.handle_v3_namespace(mock_user, 'test@example.com', 'testuser', 12345)
                assert namespace is False
                assert created is False

    def test_generate_available_namespace_name(self, mock_backend, mock_user):
        with patch.object(mock_backend, 'transform_namespace_name', return_value='testnamespace'):
            namespace_name = mock_backend.generate_available_namespace_name('testuser', 12345)
            assert namespace_name == 'testnamespace0'

    def test_validate_namespace_name_valid(self, mock_backend):
        assert mock_backend.validate_namespace_name('validname') is True

    def test_validate_namespace_name_invalid(self, mock_backend):
        assert mock_backend.validate_namespace_name('invalid__name') is False
        assert mock_backend.validate_namespace_name('1invalid') is False
        assert mock_backend.validate_namespace_name('_invalid') is False
        assert mock_backend.validate_namespace_name('v') is False

    def test_transform_namespace_name(self, mock_backend):
        assert mock_backend.transform_namespace_name('Test-User') == 'test_user'

    def test_ensure_namespace(self, mock_backend, mock_user):
        namespace, created = mock_backend._ensure_namespace('newnamespace', mock_user)
        assert namespace.name == 'newnamespace'
        assert created is True
        assert mock_user in rbac.get_v3_namespace_owners(namespace)

    def test_ensure_legacynamespace(self, mock_backend, mock_user, mock_namespace):
        legacy_namespace, created = mock_backend._ensure_legacynamespace('testuser', mock_namespace)
        assert legacy_namespace.name == 'testuser'
        assert legacy_namespace.namespace == mock_namespace
        assert created is True

    def test_get_github_access_token(self, mock_backend, mock_requests_post):
        mock_requests_post.return_value.json.return_value = {'access_token': 'access_token'}
        access_token = mock_backend.get_github_access_token('code')
        assert access_token == 'access_token'
        mock_requests_post.assert_called_once_with(
            f'{settings.SOCIAL_AUTH_GITHUB_BASE_URL}/login/oauth/access_token',
            headers={'Accept': 'application/json'},
            json={
                'code': 'code',
                'client_id': settings.SOCIAL_AUTH_GITHUB_KEY,
                'client_secret': settings.SOCIAL_AUTH_GITHUB_SECRET
            }
        )

    def test_get_github_user(self, mock_backend, mock_requests_get):
        mock_requests_get.return_value.json.return_value = {'id': 12345, 'login': 'testuser', 'email': 'testuser@example.com'}
        user_data = mock_backend.get_github_user('access_token')
        assert user_data == {'id': 12345, 'login': 'testuser', 'email': 'testuser@example.com'}
        mock_requests_get.assert_called_once_with(
            f'{settings.SOCIAL_AUTH_GITHUB_API_URL}/user',
            headers={
                'Accept': 'application/json',
                'Authorization': 'token access_token'
            },
        )

    def test_auth_complete(self, mock_backend, mock_requests_post, mock_requests_get):
        mock_requests_post.return_value.json.return_value = {'access_token': 'access_token'}
        mock_requests_get.return_value.json.return_value = {'id': 12345, 'login': 'testuser', 'email': 'testuser@example.com'}
        with patch.object(mock_backend, 'do_auth', return_value={'user': User.objects.create_user(username='testuser')}):
            request = MagicMock(GET={'code': 'code'})
            response = mock_backend.auth_complete(request=request)
            assert response['user'].username == 'testuser'

    def test_auth_complete_no_code(self, mock_backend):
        request = MagicMock(GET={})
        with pytest.raises(AuthFailed):
            mock_backend.auth_complete(request=request)

    def test_auth_complete_invalid_access_token(self, mock_backend, mock_requests_post):
        mock_requests_post.return_value.json.return_value = {}
        request = MagicMock(GET={'code': 'code'})
        with pytest.raises(AuthFailed):
            mock_backend.auth_complete(request=request)
