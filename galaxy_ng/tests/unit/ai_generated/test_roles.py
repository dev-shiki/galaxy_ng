# Import patch helper
from galaxy_ng.tests.unit.ai_generated.patch_imports import patch_test_imports
patch_test_imports()

import os
import sys
import pytest
from unittest import mock
import django
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
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# django.setup() - patched to avoid errors with mocked modules
_original_django_setup = None

def _patch_django_setup():  # Return type: global _original_django_setup
    _original_django_setup = getattr(django, 'setup')
    def noop_setup():
        # Skip actual setup which fails with mocked modules
        pass
    django.setup = noop_setup
    return _original_django_setup

@pytest.fixture
def test_pat_h():
    return str(tmp_path / "test_path")

@pytest.fixture
def test_galaxy_yam_l():
    galaxy_yaml = {
        "galaxy_info": {
            "name": "test_role",
            "namespace": "test_namespace",
            "version": "1.0.0",
        }
    }
    with open(os.path.join(test_path, "galaxy.yml"), "w") as f:
        yaml.dump(galaxy_yaml, f)
    return test_path

def test_get_path_git_roo_t():
    # Direct test of behavior with assertion on result
    result = get_path_git_root(test_path)
    assert result == test_path

def test_get_path_head_dat_e():
    # Direct test of behavior with assertion on result
    result = get_path_head_date(test_path)
    assert result.date() == datetime.date.today()

def test_get_path_role_repositor_y():
    # Direct test of behavior with assertion on result
    result = get_path_role_repository(test_path)
    assert result == "origin"

def test_get_path_role_met_a():
    # Direct test of behavior with assertion on result
    result = get_path_role_meta(test_path)
    assert result == {"galaxy_info": {"name": "test_role", "namespace": "test_namespace", "version": "1.0.0"}}

def test_get_path_role_nam_e():
    # Direct test of behavior with assertion on result
    result = get_path_role_name(test_path)
    assert result == "test_role"

def test_get_path_role_namespac_e():
    # Direct test of behavior with assertion on result
    result = get_path_role_namespace(test_path)
    assert result == "test_namespace"

def test_get_path_role_versio_n():
    # Direct test of behavior with assertion on result
    result = get_path_role_version(test_path)
    assert result == "1.0.0"

def test_path_is_rol_e():
    # Direct test of behavior with assertion on result
    result = path_is_role(test_path)
    assert result == False

def test_make_runtime_yam_l():
    # Direct test of behavior with assertion on result
    make_runtime_yaml(test_path)
    assert os.path.exists(os.path.join(test_path, "meta", "runtime.yml"))

def test_get_path_galaxy_ke_y():
    # Direct test of behavior with assertion on result
    result = get_path_galaxy_key(test_path, "name")
    assert result == "test_role"

def test_set_path_galaxy_ke_y():
    # Direct test of behavior with assertion on result
    test_path = "/tmp/test_path"
    set_path_galaxy_key(test_path, "name", "test_role")
    result = get_path_galaxy_key(test_path, "name")
    assert result == "test_role"

def test_set_path_galaxy_versio_n():
    # Direct test of behavior with assertion on result
    set_path_galaxy_version(test_path, "1.0.1")
    result = get_path_galaxy_key(test_path, "version")
    assert result == "1.0.1"

def test_set_path_galaxy_repositor_y():
    # Direct test of behavior with assertion on result
    set_path_galaxy_repository(test_path, "origin")
    result = get_path_galaxy_key(test_path, "repository")
    assert result == "origin"