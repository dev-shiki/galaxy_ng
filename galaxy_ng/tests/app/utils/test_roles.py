import sys

# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")
from django.conf import settingsimport pytest
import os
import sys
import os
import subprocess
import yaml
from unittest.mock import patch, mock_open, MagicMock
import pytest
from galaxy_ng.app.utils import roles

@pytest.fixture
def mock_subprocess_run():
    with patch('subprocess.run') as mock_run:
        yield mock_run

@pytest.fixture
def mock_os_path_exists():
    with patch('os.path.exists') as mock_exists:
        yield mock_exists

@pytest.fixture
def mock_os_makedirs():
    with patch('os.makedirs') as mock_makedirs:
        yield mock_makedirs

@pytest.fixture
def mock_glob_glob():
    with patch('glob.glob') as mock_glob:
        yield mock_glob

@pytest.fixture
def mock_yaml_safe_load():
    with patch('yaml.safe_load') as mock_load:
        yield mock_load

@pytest.fixture
def mock_yaml_dump():
    with patch('yaml.dump') as mock_dump:
        yield mock_dump

def test_get_path_git_root(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(stdout=b'/path/to/repo\n')
    assert roles.get_path_git_root('/some/path') == '/path/to/repo'

def test_get_path_head_date(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(stdout=b'2021-10-31 00:03:43 -0500\n')
    expected_date = datetime.datetime(2021, 10, 31, 0, 3, 43, tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))
    assert roles.get_path_head_date('/some/path') == expected_date

def test_get_path_role_repository(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(stdout=b'https://github.com/user/repo.git\n')
    assert roles.get_path_role_repository('/some/path') == 'https://github.com/user/repo.git'

def test_get_path_role_meta(mock_os_path_exists, mock_yaml_safe_load):
    mock_os_path_exists.return_value = True
    mock_yaml_safe_load.return_value = {'key': 'value'}
    assert roles.get_path_role_meta('/some/path') == {'key': 'value'}

def test_get_path_role_name(mock_os_path_exists, mock_yaml_safe_load, mock_subprocess_run):
    mock_os_path_exists.return_value = False
    mock_yaml_safe_load.return_value = {'galaxy_info': {'role_name': 'test_role'}}
    assert roles.get_path_role_name('/some/path') == 'test_role'

    mock_yaml_safe_load.return_value = {}
    mock_subprocess_run.return_value = MagicMock(stdout=b'https://github.com/user/ansible-role-test_role.git\n')
    assert roles.get_path_role_name('/some/path') == 'test_role'

def test_get_path_role_namespace(mock_os_path_exists, mock_subprocess_run):
    mock_os_path_exists.return_value = False
    mock_subprocess_run.return_value = MagicMock(stdout=b'https://github.com/user/repo.git\n')
    assert roles.get_path_role_namespace('/some/path') == 'user'

    mock_subprocess_run.return_value = MagicMock(stdout=b'https://github.com/ansible-collections/repo.git\n')
    assert roles.get_path_role_namespace('/some/path') == 'ansible'

def test_get_path_role_version(mock_os_path_exists, mock_yaml_safe_load, mock_subprocess_run):
    mock_os_path_exists.return_value = False
    mock_yaml_safe_load.return_value = {'version': '1.2.3'}
    assert roles.get_path_role_version('/some/path') == '1.2.3'

    mock_yaml_safe_load.return_value = {}
    mock_subprocess_run.return_value = MagicMock(stdout=b'2021-10-31 00:03:43 -0500\n')
    expected_version = '1.0.0+20211031000343'
    assert roles.get_path_role_version('/some/path') == expected_version

def test_path_is_role(mock_os_path_exists, mock_glob_glob):
    mock_os_path_exists.return_value = True
    mock_glob_glob.return_value = ['tasks', 'handlers']
    assert roles.path_is_role('/some/path') is True

    mock_glob_glob.return_value = ['plugins']
    assert roles.path_is_role('/some/path') is False

    mock_glob_glob.return_value = []
    assert roles.path_is_role('/some/path') is False

def test_make_runtime_yaml(mock_os_path_exists, mock_os_makedirs, mock_yaml_dump):
    mock_os_path_exists.return_value = False
    roles.make_runtime_yaml('/some/path')
    mock_os_makedirs.assert_called_once_with('/some/path/meta')
    mock_yaml_dump.assert_called_once_with({'requires_ansible': '>=2.10'}, f=open('/some/path/meta/runtime.yml', 'w'))

def test_get_path_galaxy_key(mock_os_path_exists, mock_yaml_safe_load):
    mock_os_path_exists.return_value = True
    mock_yaml_safe_load.return_value = {'key': 'value'}
    assert roles.get_path_galaxy_key('/some/path', 'key') == 'value'

    mock_os_path_exists.return_value = False
    assert roles.get_path_galaxy_key('/some/path', 'key') is None

def test_set_path_galaxy_key(mock_os_path_exists, mock_yaml_safe_load, mock_yaml_dump):
    mock_os_path_exists.return_value = True
    mock_yaml_safe_load.return_value = {'key': 'value'}
    roles.set_path_galaxy_key('/some/path', 'key', 'new_value')
    mock_yaml_dump.assert_called_once_with({'key': 'new_value'}, f=open('/some/path/galaxy.yml', 'w'))

def test_set_path_galaxy_version(mock_os_path_exists, mock_yaml_safe_load, mock_yaml_dump):
    mock_os_path_exists.return_value = True
    mock_yaml_safe_load.return_value = {'version': '1.2.3'}
    roles.set_path_galaxy_version('/some/path', '2.3.4')
    mock_yaml_dump.assert_called_once_with({'version': '2.3.4'}, f=open('/some/path/galaxy.yml', 'w'))

def test_set_path_galaxy_repository(mock_os_path_exists, mock_yaml_safe_load, mock_yaml_dump):
    mock_os_path_exists.return_value = True
    mock_yaml_safe_load.return_value = {'repository': 'old_repo'}
    roles.set_path_galaxy_repository('/some/path', 'new_repo')
    mock_yaml_dump.assert_called_once_with({'repository': 'new_repo'}, f=open('/some/path/galaxy.yml', 'w'))
