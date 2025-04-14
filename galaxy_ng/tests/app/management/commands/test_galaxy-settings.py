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
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.core.management.base import CommandError
from galaxy_ng.app.models.config import Setting
from galaxy_ng.app.dynamic_settings import DYNAMIC_SETTINGS_SCHEMA
from dynaconf.utils import upperfy
from dynaconf.utils.inspect import get_history


@pytest.fixture
def mock_setting():
    with patch('galaxy_ng.app.management.commands.galaxy_settings.Setting') as mock:
        yield mock


@pytest.fixture
def mock_get_history():
    with patch('galaxy_ng.app.management.commands.galaxy_settings.get_history') as mock:
        yield mock


@pytest.fixture
def mock_dynaconf_settings():
    with patch('galaxy_ng.app.management.commands.galaxy_settings.settings') as mock:
        yield mock


@pytest.mark.django_db
def test_handle_set(mock_setting):
    call_command('galaxy_settings', 'set', key='foo', value='bar')
    mock_setting.set_value_in_db.assert_called_once_with('FOO', 'bar', is_secret=False)

    call_command('galaxy_settings', 'set', key='foo', value='bar', is_secret=True)
    mock_setting.set_value_in_db.assert_called_with('FOO', 'bar', is_secret=True)


@pytest.mark.django_db
def test_handle_get(mock_setting):
    mock_setting.get_value_from_db.return_value = 'bar'
    result = call_command('galaxy_settings', 'get', key='foo', raw=True)
    assert result == 'bar'
    mock_setting.get_value_from_db.assert_called_once_with('FOO')

    mock_setting.get_value_from_db.side_effect = Setting.DoesNotExist
    result = call_command('galaxy_settings', 'get', key='foo', raw=True, default='default_value')
    assert result == 'default_value'

    mock_setting.get.return_value = 'bar'
    result = call_command('galaxy_settings', 'get', key='foo')
    assert result == 'bar'
    mock_setting.get.assert_called_once_with('FOO', default=None)


@pytest.mark.django_db
def test_handle_delete(mock_setting):
    call_command('galaxy_settings', 'delete', key='foo', all_versions=True)
    mock_setting.delete_all_versions.assert_called_once_with('FOO')

    call_command('galaxy_settings', 'delete', key='foo')
    mock_setting.delete_latest_version.assert_called_once_with('FOO')

    call_command('galaxy_settings', 'delete', all=True)
    mock_setting.objects.all().delete.assert_called_once()
    mock_setting.update_cache.assert_called_once()

    result = call_command('galaxy_settings', 'delete', key='nonexistent')
    assert result == "Nothing to delete"


@pytest.mark.django_db
def test_handle_list(mock_setting):
    mock_setting.as_dict.return_value = {'FOO': 'bar'}
    mock_setting.get.return_value = 'bar'
    result = call_command('galaxy_settings', 'list')
    assert result == {'FOO': 'bar'}
    mock_setting.get.assert_called_once_with('FOO')

    result = call_command('galaxy_settings', 'list', raw=True)
    assert result == {'FOO': 'bar'}


@pytest.mark.django_db
def test_handle_inspect(mock_get_history, mock_dynaconf_settings):
    mock_get_history.return_value = [{'key': 'FOO', 'value': 'bar'}]
    result = call_command('galaxy_settings', 'inspect', key='foo')
    assert result == [{'key': 'FOO', 'value': 'bar'}]
    mock_get_history.assert_called_once_with(mock_dynaconf_settings, 'FOO')


@pytest.mark.django_db
def test_handle_update_cache(mock_setting):
    result = call_command('galaxy_settings', 'update_cache')
    assert result is None
    mock_setting.update_cache.assert_called_once()


@pytest.mark.django_db
def test_handle_clean_cache(mock_setting):
    result = call_command('galaxy_settings', 'clean_cache')
    assert result is None
    mock_setting.clean_cache.assert_called_once()


@pytest.mark.django_db
def test_handle_allowed_keys():
    result = call_command('galaxy_settings', 'allowed_keys')
    assert result == DYNAMIC_SETTINGS_SCHEMA.keys()


@pytest.mark.django_db
def test_invalid_subcommand():
    with pytest.raises(CommandError):
        call_command('galaxy_settings', 'invalid_subcommand')
```

This test file covers all the subcommands and their respective functionalities, including edge cases and error conditions. It uses appropriate mocks and fixtures to isolate the tests and achieve high code coverage.