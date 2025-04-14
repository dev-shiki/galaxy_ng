import pytest
import logging
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.db import transaction
from social_core.backends.github import GithubOAuth2
from galaxy_ng.app.models import Namespace, LegacyNamespace
from galaxy_ng.app.utils import rbac
from galaxy_importer.constants import NAME_REGEXP
from galaxy_ng.social import GalaxyNGOAuth2

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
    strategy.authenticate.return_value = {'user': 'test_user'}
    return strategy

@pytest.fixture
def mock_rbac():
    with patch('galaxy_ng.social.rbac') as mock:
        mock.get_v3_namespace_owners.return_value = []
        mock.get_owned_v3_namespaces.return_value = []
        yield mock

@pytest.fixture
def mock_namespace():
    namespace = Namespace(name='test_namespace')
    namespace.save()
    return namespace

@pytest.fixture
def mock_legacy_namespace():
    legacy_namespace = LegacyNamespace(name='test_login')
    legacy_namespace.save()
    return legacy_namespace

def test_logged_decorator():
    @GalaxyNGOAuth2.logged
    def test_func():
        return 'test_result'

    with patch.object(logging, 'debug') as mock_logger:
        result = test_func()
        assert result == 'test_result'
        mock_logger.assert_has_calls([
            pytest.call('LOGGED: <function test_func at ...>'),
            pytest.call('LOGGED: <function test_func at ...> test_result')
        ])

def test_get_session_state(mock_strategy):
    backend = GalaxyNGOAuth2(strategy=mock_strategy, redirect_uri='http://test.com')
    assert backend.get_session_state() == 'state'

def test_do_auth(mock_strategy, mock_requests_get, mock_rbac, mock_namespace):
    mock_requests_get.return_value.json.return_value = {
        'id': 12345,
        'login': 'test_login',
        'email': 'test@example.com'
    }
    backend = GalaxyNGOAuth2(strategy=mock_strategy, redirect_uri='http://test.com')
    with patch.object(backend, 'handle_v3_namespace') as mock_handle_v3_namespace:
        mock_handle_v3_namespace.return_value = (mock_namespace, True)
        with patch.object(backend, '_ensure_legacynamespace') as mock_ensure_legacynamespace:
            mock_ensure_legacynamespace.return_value = (MagicMock(), True)
            result = backend.do_auth('test_access_token')
            assert result == {'user': 'test_user'}
            mock_handle_v3_namespace.assert_called_once_with(
                {'user': 'test_user'}, 'test@example.com', 'test_login', 12345
            )
            mock_ensure_legacynamespace.assert_called_once_with('test_login', mock_namespace)

def test_handle_v3_namespace_new_namespace(mock_strategy, mock_rbac):
    backend = GalaxyNGOAuth2(strategy=mock_strategy, redirect_uri='http://test.com')
    session_user = {'pk': 1}
    session_email = 'test@example.com'
    session_login = 'test_login'
    github_id = 12345
    with patch.object(backend, 'transform_namespace_name') as mock_transform_namespace_name:
        mock_transform_namespace_name.return_value = 'test_namespace'
        with patch.object(backend, 'validate_namespace_name') as mock_validate_namespace_name:
            mock_validate_namespace_name.return_value = True
            with patch.object(Namespace, 'objects') as mock_namespace_objects:
                mock_namespace_objects.filter.return_value.first.return_value = None
                with patch.object(backend, '_ensure_namespace') as mock_ensure_namespace:
                    mock_ensure_namespace.return_value = (MagicMock(name='test_namespace'), True)
                    namespace, created = backend.handle_v3_namespace(session_user, session_email, session_login, github_id)
                    assert namespace.name == 'test_namespace'
                    assert created is True
                    mock_ensure_namespace.assert_called_once_with('test_namespace', session_user)

def test_handle_v3_namespace_existing_namespace(mock_strategy, mock_rbac, mock_namespace):
    backend = GalaxyNGOAuth2(strategy=mock_strategy, redirect_uri='http://test.com')
    session_user = {'pk': 1}
    session_email = 'test@example.com'
    session_login = 'test_login'
    github_id = 12345
    with patch.object(backend, 'transform_namespace_name') as mock_transform_namespace_name:
        mock_transform_namespace_name.return_value = 'test_namespace'
        with patch.object(backend, 'validate_namespace_name') as mock_validate_namespace_name:
            mock_validate_namespace_name.return_value = True
            with patch.object(Namespace, 'objects') as mock_namespace_objects:
                mock_namespace_objects.filter.return_value.first.return_value = mock_namespace
                with patch.object(rbac, 'get_v3_namespace_owners') as mock_get_v3_namespace_owners:
                    mock_get_v3_namespace_owners.return_value = [session_user]
                    namespace, created = backend.handle_v3_namespace(session_user, session_email, session_login, github_id)
                    assert namespace == mock_namespace
                    assert created is False

def test_generate_available_namespace_name(mock_strategy, mock_namespace):
    backend = GalaxyNGOAuth2(strategy=mock_strategy, redirect_uri='http://test.com')
    session_login = 'test_login'
    github_id = 12345
    with patch.object(backend, 'transform_namespace_name') as mock_transform_namespace_name:
        mock_transform_namespace_name.return_value = 'test_namespace'
        with patch.object(Namespace, 'objects') as mock_namespace_objects:
            mock_namespace_objects.filter.return_value.count.side_effect = [1, 0]
            namespace_name = backend.generate_available_namespace_name(session_login, github_id)
            assert namespace_name == 'test_namespace1'

def test_validate_namespace_name():
    backend = GalaxyNGOAuth2(strategy=MagicMock(), redirect_uri='http://test.com')
    assert backend.validate_namespace_name('test_namespace') is True
    assert backend.validate_namespace_name('1test_namespace') is False
    assert backend.validate_namespace_name('test__namespace') is False
    assert backend.validate_namespace_name('_test_namespace') is False
    assert backend.validate_namespace_name('t') is False

def test_transform_namespace_name():
    backend = GalaxyNGOAuth2(strategy=MagicMock(), redirect_uri='http://test.com')
    assert backend.transform_namespace_name('test-namespace') == 'test_namespace'
    assert backend.transform_namespace_name('TEST-NAMESPACE') == 'test_namespace'

def test_ensure_namespace(mock_strategy, mock_rbac):
    backend = GalaxyNGOAuth2(strategy=mock_strategy, redirect_uri='http://test.com')
    namespace_name = 'test_namespace'
    user = {'pk': 1}
    with patch.object(Namespace, 'objects') as mock_namespace_objects:
        mock_namespace_objects.get_or_create.return_value = (MagicMock(name=namespace_name), True)
        with patch.object(rbac, 'add_user_to_v3_namespace') as mock_add_user_to_v3_namespace:
            namespace, created = backend._ensure_namespace(namespace_name, user)
            assert namespace.name == namespace_name
            assert created is True
            mock_add_user_to_v3_namespace.assert_called_once_with(user, namespace)

def test_ensure_legacynamespace(mock_strategy, mock_namespace):
    backend = GalaxyNGOAuth2(strategy=mock_strategy, redirect_uri='http://test.com')
    login = 'test_login'
    with patch.object(LegacyNamespace, 'objects') as mock_legacy_namespace_objects:
        mock_legacy_namespace_objects.get_or_create.return_value = (MagicMock(name=login), True)
        legacy_namespace, created = backend._ensure_legacynamespace(login, mock_namespace)
        assert legacy_namespace.name == login
        assert created is True
        assert legacy_namespace.namespace == mock_namespace

def test_get_github_access_token(mock_requests_post):
    backend = GalaxyNGOAuth2(strategy=MagicMock(), redirect_uri='http://test.com')
    code = 'test