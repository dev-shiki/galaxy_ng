import os
import sys
import pytest
from unittest import mock
from galaxy_ng.app.utils.roles import (
    get_path_git_root,
    get_path_head_date,
    get_path_role_repository,
    get_path_role_meta,
    get_path_role_name,
    get_path_role_namespace,
    get_path_role_version,
    path_is_role,
    make_runtime_yaml,
    get_path_galaxy_key,
    set_path_galaxy_key,
    set_path_galaxy_version,
    set_path_galaxy_repository,
)

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

@pytest.fixture
def mock_subprocess_run():
    with mock.patch('subprocess.run') as mock_run:
        yield mock_run

@pytest.fixture
def mock_open():
    with mock.patch('builtins.open') as mock_open:
        yield mock_open

@pytest.fixture
def mock_yaml_safe_load():
    with mock.patch('yaml.safe_load') as mock_load:
        yield mock_load

def test_get_path_git_root(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = b'path/to/root'
    mock_subprocess_run.return_value.returncode = 0
    assert get_path_git_root('path/to/checkout') == 'path/to/root'

def test_get_path_git_root_error(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = b''
    mock_subprocess_run.return_value.returncode = 1
    with pytest.raises(FileNotFoundError):
        get_path_git_root('path/to/checkout')

def test_get_path_head_date(mock_subprocess_run, mock_yaml_safe_load):
    mock_subprocess_run.return_value.stdout = b'2021-10-31 00:03:43 -0500'
    mock_yaml_safe_load.return_value = '2021-10-31 00:03:43 -0500'
    assert get_path_head_date('path/to/checkout') == datetime.datetime(2021, 10, 31, 0, 3, 43, tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))

def test_get_path_head_date_error(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = b''
    with pytest.raises(ValueError):
        get_path_head_date('path/to/checkout')

def test_get_path_role_repository(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = b'https://github.com/user/repo'
    assert get_path_role_repository('path/to/checkout') == 'https://github.com/user/repo'

def test_get_path_role_repository_error(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = b''
    with pytest.raises(FileNotFoundError):
        get_path_role_repository('path/to/checkout')

def test_get_path_role_meta(mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = 'meta: main.yml'
    assert get_path_role_meta('path/to/checkout') == {'meta': 'main.yml'}

def test_get_path_role_name(mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = 'name: my_role'
    assert get_path_role_name('path/to/checkout') == 'my_role'

def test_get_path_role_name_error(mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = ''
    assert get_path_role_name('path/to/checkout') is None

def test_get_path_role_namespace(mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = 'namespace: my_namespace'
    assert get_path_role_namespace('path/to/checkout') == 'my_namespace'

def test_get_path_role_namespace_error(mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = ''
    assert get_path_role_namespace('path/to/checkout') is None

def test_get_path_role_version(mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = 'version: 1.0.0'
    assert get_path_role_version('path/to/checkout') == '1.0.0'

def test_get_path_role_version_error(mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = ''
    assert get_path_role_version('path/to/checkout') is None

def test_path_is_role():
    assert path_is_role('path/to/role') is True

def test_path_is_role_error():
    assert path_is_role('path/to/not_a_role') is False

def test_make_runtime_yaml(mock_open):
    make_runtime_yaml('path/to/role')
    mock_open.assert_called_once_with('path/to/role/meta/runtime.yml', 'w')

def test_get_path_galaxy_key(mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = 'key: value'
    assert get_path_galaxy_key('path/to/role') == {'key': 'value'}

def test_get_path_galaxy_key_error(mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = ''
    assert get_path_galaxy_key('path/to/role') is None

def test_set_path_galaxy_key(mock_open):
    set_path_galaxy_key('path/to/role', 'key', 'value')
    mock_open.assert_called_once_with('path/to/role/galaxy.yml', 'w')

def test_set_path_galaxy_version(mock_open):
    set_path_galaxy_version('path/to/role', '1.0.0')
    mock_open.assert_called_once_with('path/to/role/galaxy.yml', 'w')

def test_set_path_galaxy_repository(mock_open):
    set_path_galaxy_repository('path/to/role', 'https://github.com/user/repo')
    mock_open.assert_called_once_with('path/to/role/galaxy.yml', 'w')
