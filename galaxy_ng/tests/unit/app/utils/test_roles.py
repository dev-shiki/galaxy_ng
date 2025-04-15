import sys

# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")
from django.conf import settingsimport pytest
import os
import sys
import pytest
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
from unittest.mock import patch, MagicMock
import os
import yaml
import glob
import subprocess
from datetime import datetime

@pytest.fixture
def mock_git_root():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = b'/path/to/repo'
        yield mock_run

@pytest.fixture
def mock_git_head_date():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = b'2021-01-01 00:00:00 -0500'
        yield mock_run

@pytest.fixture
def mock_git_remote():
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = b'https://github.com/user/repo.git'
        yield mock_run

@pytest.fixture
def mock_galaxy_key():
    with patch('galaxy_ng.app.utils.roles.yaml.safe_load') as mock_safe_load:
        mock_safe_load.return_value = {'key': 'value'}
        yield mock_safe_load

@pytest.fixture
def mock_galaxy_key_none():
    with patch('galaxy_ng.app.utils.roles.yaml.safe_load') as mock_safe_load:
        mock_safe_load.return_value = None
        yield mock_safe_load

@pytest.fixture
def mock_galaxy_key_empty():
    with patch('galaxy_ng.app.utils.roles.yaml.safe_load') as mock_safe_load:
        mock_safe_load.return_value = {}
        yield mock_safe_load

def test_get_path_git_root(mock_git_root):
    assert get_path_git_root('/path/to/repo') == '/path_is_role('/path/to/repo')

def test_get_path_head_date(mock_git_head_date):
    assert get_path_head_date('/path/to/repo') == datetime(2021, 1, 1, 0, 0, 0, -30000)

def test_get_path_role_repository(mock_git_remote):
    assert get_path_role_repository('/path/to/repo') == 'https://github.com/user/repo.git'

def test_get_path_role_meta(tmp_path):
    metaf = os.path.join(tmp_path, 'meta', 'main.yml')
    with open(metaf, 'w') as f:
        yaml.dump({'key': 'value'}, f)
    assert get_path_role_meta('/path/to/repo') == {'key': 'value'}

def test_get_path_role_name(mock_galaxy_key):
    assert get_path_role_name('/path/to/repo') == 'key'

def test_get_path_role_name_none(mock_galaxy_key_none):
    assert get_path_role_name('/path/to/repo') is None

def test_get_path_role_name_empty(mock_galaxy_key_empty):
    assert get_path_role_name('/path/to/repo') is None

def test_get_path_role_namespace(mock_galaxy_key):
    assert get_path_role_namespace('/path/to/repo') == 'key'

def test_get_path_role_namespace_none(mock_galaxy_key_none):
    assert get_path_role_namespace('/path/to/repo') is None

def test_get_path_role_namespace_empty(mock_galaxy_key_empty):
    assert get_path_role_namespace('/path/to/repo') is None

def test_get_path_role_version(mock_galaxy_key):
    assert get_path_role_version('/path/to/repo') == 'key'

def test_get_path_role_version_none(mock_galaxy_key_none):
    assert get_path_role_version('/path/to/repo') is None

def test_get_path_role_version_empty(mock_galaxy_key_empty):
    assert get_path_role_version('/path/to/repo') is None

def test_path_is_role(tmp_path):
    assert path_is_role('/path/to/repo') is False

def test_path_is_role_tasks(tmp_path):
    os.makedirs(os.path.join(tmp_path, 'tasks'))
    assert path_is_role('/path/to/repo') is True

def test_path_is_role_library(tmp_path):
    os.makedirs(os.path.join(tmp_path, 'library'))
    assert path_is_role('/path/to/repo') is True

def test_path_is_role_handlers(tmp_path):
    os.makedirs(os.path.join(tmp_path, 'handlers'))
    assert path_is_role('/path/to/repo') is True

def test_path_is_role_defaults(tmp_path):
    os.makedirs(os.path.join(tmp_path, 'defaults'))
    assert path_is_role('/path/to/repo') is True

def test_make_runtime_yaml(tmp_path):
    make_runtime_yaml('/path/to/repo')
    runtimef = os.path.join(tmp_path, 'meta', 'runtime.yml')
    assert os.path.exists(runtimef)

def test_get_path_galaxy_key(tmp_path):
    gfn = os.path.join(tmp_path, 'galaxy.yml')
    with open(gfn, 'w') as f:
        yaml.dump({'key': 'value'}, f)
    assert get_path_galaxy_key('/path/to/repo') == {'key': 'value'}

def test_get_path_galaxy_key_none(tmp_path):
    gfn = os.path.join(tmp_path, 'galaxy.yml')
    with open(gfn, 'w') as f:
        yaml.dump(None, f)
    assert get_path_galaxy_key('/path/to/repo') is None

def test_get_path_galaxy_key_empty(tmp_path):
    gfn = os.path.join(tmp_path, 'galaxy.yml')
    with open(gfn, 'w') as f:
        yaml.dump({}, f)
    assert get_path_galaxy_key('/path/to/repo') is None

def test_set_path_galaxy_key(tmp_path):
    gfn = os.path.join(tmp_path, 'galaxy.yml')
    with open(gfn, 'w') as f:
        yaml.dump({'key': 'value'}, f)
    set_path_galaxy_key('/path/to/repo', 'new_key', 'new_value')
    with open(gfn, 'r') as f:
        assert yaml.safe_load(f.read()) == {'new_key': 'new_value'}

def test_set_path_galaxy_version(tmp_path):
    gfn = os.path.join(tmp_path, 'galaxy.yml')
    with open(gfn, 'w') as f:
        yaml.dump({'version': 'old_version'}, f)
    set_path_galaxy_version('/path/to/repo', 'new_version')
    with open(gfn, 'r') as f:
        assert yaml.safe_load(f.read()) == {'version': 'new_version'}

def test_set_path_galaxy_repository(tmp_path):
    gfn = os.path.join(tmp_path, 'galaxy.yml')
    with open(gfn, 'w') as f:
        yaml.dump({'repository': 'old_repository'}, f)
    set_path_galaxy_repository('/path/to/repo', 'new_repository')
    with open(gfn, 'r') as f:
        assert yaml.safe_load(f.read()) == {'repository': 'new_repository'}
