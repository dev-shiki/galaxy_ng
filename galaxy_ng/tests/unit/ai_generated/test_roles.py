import os
import sys
import re
import pytest
from unittest import mock
from django.conf import settings
from galaxy_ng.app.utils import roles

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

# Mocks
@pytest.fixture
def mock_path():
    return mock.MagicMock()

@pytest.fixture
def mock_subprocess_run():
    return mock.MagicMock()

@pytest.fixture
def mock_os_path_exists():
    return mock.MagicMock()

@pytest.fixture
def mock_os_path_join():
    return mock.MagicMock()

@pytest.fixture
def mock_yaml_safe_load():
    return mock.MagicMock()

@pytest.fixture
def mock_yaml_dump():
    return mock.MagicMock()

# Fixtures
@pytest.fixture
def mock_gfn(mock_path):
    return os.path.join(mock_path, 'galaxy.yml')

@pytest.fixture
def mock_gfn_not_exists(mock_path):
    return os.path.join(mock_path, 'non_existent_file.yml')

@pytest.fixture
def mock_gfn_empty(mock_path):
    return os.path.join(mock_path, 'empty_file.yml')

# Test classes and functions
class TestRoles:
    def test_get_path_git_root(self, mock_path, mock_subprocess_run):
        mock_subprocess_run.stdout = b'path/to/root'
        mock_subprocess_run.return_value = mock_subprocess_run
        assert roles.get_path_git_root(mock_path) == 'path/to/root'

    def test_get_path_git_root_error(self, mock_path, mock_subprocess_run):
        mock_subprocess_run.return_value = mock_subprocess_run
        with pytest.raises(FileNotFoundError):
            roles.get_path_git_root(mock_path)

    def test_get_path_head_date(self, mock_path, mock_subprocess_run):
        mock_subprocess_run.stdout = b'2021-10-31 00:03:43 -0500'
        mock_subprocess_run.return_value = mock_subprocess_run
        assert roles.get_path_head_date(mock_path) == datetime.datetime(2021, 10, 31, 0, 3, 43, tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))

    def test_get_path_head_date_error(self, mock_path, mock_subprocess_run):
        mock_subprocess_run.return_value = mock_subprocess_run
        with pytest.raises(FileNotFoundError):
            roles.get_path_head_date(mock_path)

    def test_get_path_role_repository(self, mock_path, mock_subprocess_run):
        mock_subprocess_run.stdout = b'https://github.com/user/repo'
        mock_subprocess_run.return_value = mock_subprocess_run
        assert roles.get_path_role_repository(mock_path) == 'https://github.com/user/repo'

    def test_get_path_role_repository_error(self, mock_path, mock_subprocess_run):
        mock_subprocess_run.return_value = mock_subprocess_run
        with pytest.raises(FileNotFoundError):
            roles.get_path_role_repository(mock_path)

    def test_get_path_role_meta(self, mock_path, mock_os_path_exists, mock_yaml_safe_load):
        mock_os_path_exists.return_value = True
        mock_yaml_safe_load.return_value = {'key': 'value'}
        assert roles.get_path_role_meta(mock_path) == {'key': 'value'}

    def test_get_path_role_meta_error(self, mock_path, mock_os_path_exists):
        mock_os_path_exists.return_value = False
        with pytest.raises(FileNotFoundError):
            roles.get_path_role_meta(mock_path)

    def test_get_path_role_name(self, mock_path, mock_yaml_safe_load):
        mock_yaml_safe_load.return_value = {'galaxy_info': {'role_name': 'role_name'}}
        assert roles.get_path_role_name(mock_path) == 'role_name'

    def test_get_path_role_name_error(self, mock_path, mock_yaml_safe_load):
        mock_yaml_safe_load.return_value = {}
        assert roles.get_path_role_name(mock_path) == 'user/repo'

    def test_get_path_role_namespace(self, mock_path, mock_yaml_safe_load):
        mock_yaml_safe_load.return_value = {'galaxy_info': {'namespace': 'namespace'}}
        assert roles.get_path_role_namespace(mock_path) == 'namespace'

    def test_get_path_role_namespace_error(self, mock_path, mock_yaml_safe_load):
        mock_yaml_safe_load.return_value = {}
        assert roles.get_path_role_namespace(mock_path) == 'user'

    def test_get_path_role_version(self, mock_path, mock_yaml_safe_load):
        mock_yaml_safe_load.return_value = {'galaxy_info': {'version': 'version'}}
        assert roles.get_path_role_version(mock_path) == 'version'

    def test_get_path_role_version_error(self, mock_path, mock_yaml_safe_load):
        mock_yaml_safe_load.return_value = {}
        assert roles.get_path_role_version(mock_path) == '2021-10-31+10+31+00+03+43-0500'

    def test_path_is_role(self, mock_path):
        assert roles.path_is_role(mock_path) == False

    def test_path_is_role_error(self, mock_path):
        mock_path = os.path.join(mock_path, 'tasks')
        assert roles.path_is_role(mock_path) == True

    def test_make_runtime_yaml(self, mock_path, mock_os_path_exists, mock_os_path_join):
        mock_os_path_exists.return_value = False
        roles.make_runtime_yaml(mock_path)
        assert os.path.exists(os.path.join(mock_path, 'meta', 'runtime.yml'))

    def test_make_runtime_yaml_error(self, mock_path, mock_os_path_exists):
        mock_os_path_exists.return_value = True
        with pytest.raises(FileExistsError):
            roles.make_runtime_yaml(mock_path)

    def test_get_path_galaxy_key(self, mock_path, mock_yaml_safe_load):
        mock_yaml_safe_load.return_value = {'key': 'value'}
        assert roles.get_path_galaxy_key(mock_path, 'key') == 'value'

    def test_get_path_galaxy_key_error(self, mock_path, mock_yaml_safe_load):
        mock_yaml_safe_load.return_value = {}
        assert roles.get_path_galaxy_key(mock_path, 'key') == None

    def test_set_path_galaxy_key(self, mock_path, mock_yaml_safe_load):
        roles.set_path_galaxy_key(mock_path, 'key', 'value')
        mock_yaml_safe_load.return_value = {'key': 'value'}

    def test_set_path_galaxy_version(self, mock_path, mock_yaml_safe_load):
        roles.set_path_galaxy_version(mock_path, 'version')
        mock_yaml_safe_load.return_value = {'version': 'version'}

    def test_set_path_galaxy_repository(self, mock_path, mock_yaml_safe_load):
        roles.set_path_galaxy_repository(mock_path, 'repository')
        mock_yaml_safe_load.return_value = {'repository': 'repository'}
