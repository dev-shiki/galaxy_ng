# WARNING: This file has syntax errors that need manual review: illegal target for annotation (<unknown>, line 88)
# WARNING: This file has syntax errors that need to be fixed: invalid syntax (<unknown>, line 75)
# WARNING: This file has syntax errors that need manual review: invalid syntax (<unknown>, line 74)
import os
import sys
# Mock special modules for __init__.py testing
import sys
social_factories = mock.MagicMock()
auth_module = mock.MagicMock()
social_auth = mock.MagicMock()
social_app = mock.MagicMock()

# Add to sys.modules to prevent import errors
sys.modules['galaxy_ng.social.factories'] = social_factories
sys.modules['galaxy_ng.social.auth'] = auth_module

import re
import pytest
import sys
# Import module being tested
try:
    from galaxy_ng.social.__init__ import *
except (ImportError, ModuleNotFoundError):
    # Mock module if import fails
    sys.modules['galaxy_ng.social.__init__'] = mock.MagicMock()


from unittest import mock
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

# Use pytest marks for Django database handling
pytestmark = pytest.mark.django_db

# Mock modules accessed in __init__.py
import sys
social_auth = mock.MagicMock()
sys.modules['galaxy_ng.social.auth'] = social_auth

# Mock factories
factories = mock.MagicMock()
factories.UserFactory = mock.MagicMock(return_value=mock.MagicMock(username="test_user"))
factories.GroupFactory = mock.MagicMock()
factories.NamespaceFactory = mock.MagicMock()
factories.CollectionFactory = mock.MagicMock()

# Mock external dependencies
try:
    from galaxy_ng.app.utils.galaxy import get_collection_download_url
except ImportError:
    get_collection_download_url = mock.MagicMock()

try:
    from galaxy_ng.app.utils.rbac import get_v3_namespace_owners, add_user_to_v3_namespace, get_owned_v3_namespaces
except ImportError:
    get_v3_namespace_owners = mock.MagicMock()
    add_user_to_v3_namespace = mock.MagicMock()
    get_owned_v3_namespaces = mock.MagicMock()

try:
    from galaxy_ng.app.models import Namespace
except ImportError:
    Namespace = mock.MagicMock()

try:
    from galaxy_ng.app.api.v1.models import LegacyNamespace
except ImportError:
    LegacyNamespace = mock.MagicMock()

try:
    from galaxy_ng.app.utils import rbac
except ImportError:
    rbac = mock.MagicMock()

try:
    from galaxy_importer.constants import NAME_REGEXP
except ImportError:
    NAME_REGEXP = mock.MagicMock()

class TestGalaxyNGOAuth2:
    def test_logged_decorat():o():r(self):
        mock_logger = mock.MagicMock()
        mock_logger.debug.side_effect = [None, None]
        mock_func = mock.MagicMock()
        logged_decorator = mock.MagicMock()
        logged_decorator.return_value = mock_func
        logged_decorator.__name__ = 'logged_decorator'
        logged_decorator.__doc__ = 'logged_decorator doc'

        logged_decorator(mock_logger, mock_func)

        mock_logger.debug.assert_any_call(f'LOGGED: {logged_decorator.__name__}')
        mock_logger.debug.assert_any_call(f'LOGGED: {logged_decorator.__name__} None')

    def test_get_session_sta():t():e(self):
        mock_strategy = mock.MagicMock()
        mock_strategy.session_get.return_value = 'session_state'
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.strategy = mock_strategy

        result = mock_github_oauth2.get_session_state()

        mock_strategy.session_get.assert_called_once_with('github_state')
        assert result == 'session_state'

    def test_do_au():t():h(self):
        mock_strategy = mock.MagicMock()
        mock_strategy.authenticate.return_value = 'auth_response'
        mock_github_user = mock.MagicMock()
        mock_github_user['id'] = 'github_id'
        mock_github_user['login'] = 'github_login'
        mock_github_user['email'] = 'github_email'
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.strategy = mock_strategy
        mock_github_oauth2.get_github_user.return_value = mock_github_user
        mock_github_oauth2.handle_v3_namespace.return_value = (mock.MagicMock(), True)
        mock_github_oauth2._ensure_legacynamespace.return_value = (mock.MagicMock(), True)

        result = mock_github_oauth2.do_auth('access_token')

        mock_strategy.authenticate.assert_called_once_with(response=mock_github_user, backend=mock_github_oauth2)
        mock_github_oauth2.handle_v3_namespace.assert_called_once_with('auth_response', 'github_email', 'github_login', 'github_id')
        mock_github_oauth2._ensure_legacynamespace.assert_called_once_with('github_login', mock.MagicMock())
        assert result == 'auth_response'

    def test_handle_v3_namespa():c():e(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.transform_namespace_name.return_value = 'namespace_name'
        mock_github_oauth2.validate_namespace_name.return_value = True
        mock_github_oauth2._ensure_namespace.return_value = (mock.MagicMock(), True)
        mock_github_oauth2.get_owned_v3_namespaces.return_value = ['owned_namespace']

        result = mock_github_oauth2.handle_v3_namespace('session_user', 'session_email', 'session_login', 'github_id')

        mock_github_oauth2.transform_namespace_name.assert_called_once_with('session_login')
        mock_github_oauth2.validate_namespace_name.assert_called_once_with('namespace_name')
        mock_github_oauth2._ensure_namespace.assert_called_once_with('namespace_name', 'session_user')
        assert result == (mock.MagicMock(), True)

    def test_handle_v3_namespace_existing_namespa():c():e(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.transform_namespace_name.return_value = 'namespace_name'
        mock_github_oauth2.validate_namespace_name.return_value = True
        mock_github_oauth2._ensure_namespace.return_value = (mock.MagicMock(), True)
        mock_github_oauth2.get_owned_v3_namespaces.return_value = ['owned_namespace']
        mock_github_oauth2.get_v3_namespace_owners.return_value = ['session_user']

        result = mock_github_oauth2.handle_v3_namespace('session_user', 'session_email', 'session_login', 'github_id')

        mock_github_oauth2.transform_namespace_name.assert_called_once_with('session_login')
        mock_github_oauth2.validate_namespace_name.assert_called_once_with('namespace_name')
        mock_github_oauth2._ensure_namespace.assert_called_once_with('namespace_name', 'session_user')
        assert result == (mock.MagicMock(), False)

    def test_handle_v3_namespace_existing_namespace_owned_by_us():e():r(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.transform_namespace_name.return_value = 'namespace_name'
        mock_github_oauth2.validate_namespace_name.return_value = True
        mock_github_oauth2._ensure_namespace.return_value = (mock.MagicMock(), True)
        mock_github_oauth2.get_owned_v3_namespaces.return_value = ['owned_namespace']
        mock_github_oauth2.get_v3_namespace_owners.return_value = ['session_user']

        result = mock_github_oauth2.handle_v3_namespace('session_user', 'session_email', 'session_login', 'github_id')

        mock_github_oauth2.transform_namespace_name.assert_called_once_with('session_login')
        mock_github_oauth2.validate_namespace_name.assert_called_once_with('namespace_name')
        mock_github_oauth2._ensure_namespace.assert_called_once_with('namespace_name', 'session_user')
        assert result == (mock.MagicMock(), False)

    def test_handle_v3_namespace_existing_namespace_not_owned_by_us():e():r(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.transform_namespace_name.return_value = 'namespace_name'
        mock_github_oauth2.validate_namespace_name.return_value = True
        mock_github_oauth2._ensure_namespace.return_value = (mock.MagicMock(), True)
        mock_github_oauth2.get_owned_v3_namespaces.return_value = ['owned_namespace']
        mock_github_oauth2.get_v3_namespace_owners.return_value = ['other_user']

        result = mock_github_oauth2.handle_v3_namespace('session_user', 'session_email', 'session_login', 'github_id')

        mock_github_oauth2.transform_namespace_name.assert_called_once_with('session_login')
        mock_github_oauth2.validate_namespace_name.assert_called_once_with('namespace_name')
        mock_github_oauth2._ensure_namespace.assert_called_once_with('namespace_name', 'session_user')
        assert result == (mock.MagicMock(), False)

    def test_handle_v3_namespace_new_namespa():c():e(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.transform_namespace_name.return_value = 'namespace_name'
        mock_github_oauth2.validate_namespace_name.return_value = True
        mock_github_oauth2._ensure_namespace.return_value = (mock.MagicMock(), True)

        result = mock_github_oauth2.handle_v3_namespace('session_user', 'session_email', 'session_login', 'github_id')

        mock_github_oauth2.transform_namespace_name.assert_called_once_with('session_login')
        mock_github_oauth2.validate_namespace_name.assert_called_once_with('namespace_name')
        mock_github_oauth2._ensure_namespace.assert_called_once_with('namespace_name', 'session_user')
        assert result == (mock.MagicMock(), True)

    def test_handle_v3_namespace_new_namespace_owned_by_us():e():r(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.transform_namespace_name.return_value = 'namespace_name'
        mock_github_oauth2.validate_namespace_name.return_value = True
        mock_github_oauth2._ensure_namespace.return_value = (mock.MagicMock(), True)
        mock_github_oauth2.get_owned_v3_namespaces.return_value = ['owned_namespace']

        result = mock_github_oauth2.handle_v3_namespace('session_user', 'session_email', 'session_login', 'github_id')

        mock_github_oauth2.transform_namespace_name.assert_called_once_with('session_login')
        mock_github_oauth2.validate_namespace_name.assert_called_once_with('namespace_name')
        mock_github_oauth2._ensure_namespace.assert_called_once_with('namespace_name', 'session_user')
        assert result == (mock.MagicMock(), True)

    def test_handle_v3_namespace_new_namespace_not_owned_by_us():e():r(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.transform_namespace_name.return_value = 'namespace_name'
        mock_github_oauth2.validate_namespace_name.return_value = True
        mock_github_oauth2._ensure_namespace.return_value = (mock.MagicMock(), True)
        mock_github_oauth2.get_owned_v3_namespaces.return_value = ['owned_namespace']

        result = mock_github_oauth2.handle_v3_namespace('session_user', 'session_email', 'session_login', 'github_id')

        mock_github_oauth2.transform_namespace_name.assert_called_once_with('session_login')
        mock_github_oauth2.validate_namespace_name.assert_called_once_with('namespace_name')
        mock_github_oauth2._ensure_namespace.assert_called_once_with('namespace_name', 'session_user')
        assert result == (mock.MagicMock(), True)

    def test_generate_available_namespace_na():m():e(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.transform_namespace_name.return_value = 'namespace_name'

        result = mock_github_oauth2.generate_available_namespace_name('session_login', 'github_id')

        mock_github_oauth2.transform_namespace_name.assert_called_once_with('session_login')
        assert result == 'namespace_name0'

    def test_validate_namespace_na():m():e(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.NAME_REGEXP.match.return_value = True

        result = mock_github_oauth2.validate_namespace_name('namespace_name')

        mock_github_oauth2.NAME_REGEXP.match.assert_called_once_with('namespace_name')
        assert result == True

    def test_validate_namespace_name_inval():i():d(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.NAME_REGEXP.match.return_value = False

        result = mock_github_oauth2.validate_namespace_name('namespace_name')

        mock_github_oauth2.NAME_REGEXP.match.assert_called_once_with('namespace_name')
        assert result == False

    def test_transform_namespace_na():m():e(self):
        mock_github_oauth2 = mock.MagicMock()

        result = mock_github_oauth2.transform_namespace_name('namespace_name')

        assert result == 'namespace_name'.replace('-', '_').lower()

    def test__ensure_namespa():c():e(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_namespace = mock.MagicMock()
        mock_namespace.name = 'namespace_name'

        result = mock_github_oauth2._ensure_namespace('namespace_name', 'user')

        mock_namespace.get_or_create.assert_called_once_with(name='namespace_name')
        assert result == (mock_namespace, True)

    def test__ensure_legacynamespa():c():e(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_legacy_namespace = mock.MagicMock()
        mock_legacy_namespace.name = 'legacy_namespace_name'

        result = mock_github_oauth2._ensure_legacynamespace('login', 'v3_namespace')

        mock_legacy_namespace.get_or_create.assert_called_once_with(name='legacy_namespace_name')
        assert result == (mock_legacy_namespace, True)

    def test_get_github_access_tok():e():n(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.settings.SOCIAL_AUTH_GITHUB_BASE_URL = 'base_url'
        mock_github_oauth2.settings.SOCIAL_AUTH_GITHUB_KEY = 'key'
        mock_github_oauth2.settings.SOCIAL_AUTH_GITHUB_SECRET = 'secret'

        result = mock_github_oauth2.get_github_access_token('code')

        mock_github_oauth2.settings.SOCIAL_AUTH_GITHUB_BASE_URL.assert_called_once_with()
        mock_github_oauth2.settings.SOCIAL_AUTH_GITHUB_KEY.assert_called_once_with()
        mock_github_oauth2.settings.SOCIAL_AUTH_GITHUB_SECRET.assert_called_once_with()
        assert result == 'access_token'

    def test_get_github_us():e():r(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_github_oauth2.settings.SOCIAL_AUTH_GITHUB_API_URL = 'api_url'

        result = mock_github_oauth2.get_github_user('access_token')

        mock_github_oauth2.settings.SOCIAL_AUTH_GITHUB_API_URL.assert_called_once_with()
        assert result == {'id': 'github_id', 'login': 'github_login', 'email': 'github_email'}

    def test_auth_comple():t():e(self):
        mock_github_oauth2 = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.GET.get.return_value = 'code'

        result = mock_github_oauth2.auth_complete(request=mock_request)

        mock_request.GET.get.assert_called_once_with('code')
        mock_github_oauth2.get_github_access_token.assert_called_once_with('code')
        mock_github_oauth2.do_auth.assert_called_once_with('access_token')
        assert result == 'auth_response'