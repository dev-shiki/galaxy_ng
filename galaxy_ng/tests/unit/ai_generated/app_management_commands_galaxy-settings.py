  import os

  import sys

  import re

  import pytest

  from unittest import mock

  

  # Setup Django environment

  os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")

  # Add project root to path if needed

  project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))

  if project_root not in sys.path:

      sys.path.insert(0, project_root)

  

  import django

  django.setup()

  

  # Use pytest marks for Django database handling

  pytestmark = pytest.mark.django_db

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
from galaxy_ng.app.models.config import Setting
from galaxy_ng.app.dynamic_settings import DYNAMIC_SETTINGS_SCHEMA
from galaxy_ng.app.management.commands.galaxy_settings import Command
from django.core.management import call_command
from django.core.management.base import CommandError
from django.conf import settings

@pytest.fixture
def mock_settings():
    with mock.patch.dict('sys.modules', {'django.conf': mock.Mock()}):
        yield

@pytest.fixture
def mock_dynaconf():
    with mock.patch('galaxy_ng.app.dynamic_settings.DYNAMIC_SETTINGS_SCHEMA', {}):
        yield

@pytest.fixture
def mock_setting():
    with mock.patch.object(Setting, 'set_value_in_db', return_value=None):
        with mock.patch.object(Setting, 'get_value_from_db', return_value=None):
            with mock.patch.object(Setting, 'delete_latest_version', return_value=None):
                with mock.patch.object(Setting, 'delete_all_versions', return_value=None):
                    with mock.patch.object(Setting, 'update_cache', return_value=None):
                        with mock.patch.object(Setting, 'clean_cache', return_value=None):
                            yield

class TestGalaxySettingsCommand:
    def test_handle_set(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_set(key='test_key', value='test_value', is_secret=False)
        assert result is None

    def test_handle_set_with_secret(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_set(key='test_key', value='test_value', is_secret=True)
        assert result is None

    def test_handle_get(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_get(key='test_key', raw=False, default='default_value')
        assert result == 'default_value'

    def test_handle_get_raw(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_get(key='test_key', raw=True, default='default_value')
        assert result is None

    def test_handle_delete(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_delete(key='test_key', all_versions=False, all_settings=False)
        assert result == "Nothing to delete"

    def test_handle_delete_all_versions(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_delete(key='test_key', all_versions=True, all_settings=False)
        assert result is None

    def test_handle_delete_all_settings(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_delete(key=None, all_versions=False, all_settings=True)
        assert result is None

    def test_handle_list(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_list(raw=False)
        assert result == {}

    def test_handle_list_raw(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_list(raw=True)
        assert result == {}

    def test_handle_inspect(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_inspect(key='test_key')
        assert result is None

    def test_handle_update_cache(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_update_cache()
        assert result is None

    def test_handle_clean_cache(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_clean_cache()
        assert result is None

    def test_handle_allowed_keys(self, mock_settings, mock_dynaconf, mock_setting):
        command = Command()
        result = command.handle_allowed_keys()
        assert result == DYNAMIC_SETTINGS_SCHEMA.keys()

    def test_call_command_set(self, mock_settings, mock_dynaconf, mock_setting):
        with mock.patch.object(Command, 'handle_set', return_value=None):
            call_command('galaxy_settings', 'set', 'test_key', 'test_value', is_secret=False)
            assert True

    def test_call_command_get(self, mock_settings, mock_dynaconf, mock_setting):
        with mock.patch.object(Command, 'handle_get', return_value=None):
            call_command('galaxy_settings', 'get', 'test_key', raw=False, default='default_value')
            assert True

    def test_call_command_delete(self, mock_settings, mock_dynaconf, mock_setting):
        with mock.patch.object(Command, 'handle_delete', return_value=None):
            call_command('galaxy_settings', 'delete', 'test_key', all_versions=False, all_settings=False)
            assert True

    def test_call_command_list(self, mock_settings, mock_dynaconf, mock_setting):
        with mock.patch.object(Command, 'handle_list', return_value=None):
            call_command('galaxy_settings', 'list', raw=False)
            assert True

    def test_call_command_inspect(self, mock_settings, mock_dynaconf, mock_setting):
        with mock.patch.object(Command, 'handle_inspect', return_value=None):
            call_command('galaxy_settings', 'inspect', 'test_key')
            assert True

    def test_call_command_update_cache(self, mock_settings, mock_dynaconf, mock_setting):
        with mock.patch.object(Command, 'handle_update_cache', return_value=None):
            call_command('galaxy_settings', 'update_cache')
            assert True

    def test_call_command_clean_cache(self, mock_settings, mock_dynaconf, mock_setting):
        with mock.patch.object(Command, 'handle_clean_cache', return_value=None):
            call_command('galaxy_settings', 'clean_cache')
            assert True

    def test_call_command_allowed_keys(self, mock_settings, mock_dynaconf, mock_setting):
        with mock.patch.object(Command, 'handle_allowed_keys', return_value=None):
            call_command('galaxy_settings', 'allowed_keys')
            assert True

    def test_call_command_invalid_subcommand(self, mock_settings, mock_dynaconf, mock_setting):
        with pytest.raises(CommandError):
            call_command('galaxy_settings', 'invalid_subcommand')
