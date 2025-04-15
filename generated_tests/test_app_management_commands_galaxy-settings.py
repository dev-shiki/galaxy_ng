import pytest
from django.core.management import call_command
from galaxy_ng.app.models.config import Setting
from galaxy_ng.app.dynamic_settings import DYNAMIC_SETTINGS_SCHEMA
from galaxy_ng.tests.app.conftest import settings_with_dynamic_settings

@pytest.fixture
def settings_with_galaxy_settings(settings_with_dynamic_settings):
    call_command('galaxy-settings', 'set', '--key', 'foo', '--value', 'bar')
    return settings_with_dynamic_settings

@pytest.mark.django_db
def test_handle_set(settings_with_galaxy_settings):
    result = call_command('galaxy-settings', 'set', '--key', 'foo', '--value', 'baz')
    assert Setting.objects.get(key='foo').value == 'baz'

@pytest.mark.django_db
def test_handle_get(settings_with_galaxy_settings):
    result = call_command('galaxy-settings', ' 'get', '--key', 'foo')
    assert result == 'bar'

@pytest.mark.django_db
def test_handle_get_raw(settings_with_galaxy_settings):
    result = call_command('galaxy-settings', 'get', '--key', 'foo', '--raw')
    assert result == 'bar'

@pytest.mark.django_db
def test_handle_get_default(settings_with_galaxy_settings):
    result = call_command('galaxy-settings', 'get', '--key', 'non_existent_key', '--default', 'default_value')
    assert result == 'default_value'

@pytest.mark.django_db
def test_handle_delete(settings_with_galaxy_settings):
    result = call_command('galaxy-settings', 'delete', '--key', 'foo')
    assert Setting.objects.filter(key='foo').exists() is False

@pytest.mark.django_db
def test_handle_delete_all_versions(settings_with_galaxy_settings):
    call_command('galaxy-settings', 'set', '--key', 'foo', '--value', 'bar')
    call_command('galaxy-settings', 'set', '--key', 'foo', '--value', 'baz')
    result = call_command('galaxy-settings', 'delete', '--key', 'foo', '--all-versions')
    assert Setting.objects.filter(key='foo').exists() is False

@pytest.mark.django_db
def test_handle_delete_all(settings_with_galaxy_settings):
    call_command('galaxy-settings', 'set', '--key', 'foo', '--value', 'bar')
    call_command('galaxy-settings', 'set', '--key', 'baz', '--value', 'qux')
    result = call_command('galaxy-settings', 'delete', '--all')
    assert Setting.objects.all().exists() is False

@pytest.mark.django_db
def test_handle_list(settings_with_galaxy_settings):
    result = call_command('galaxy-settings', 'list')
    assert 'foo' in result

@pytest.mark.django_db
def test_handle_list_raw(settings_with_galaxy_settings):
    result = call_command('galaxy-settings', 'list', '--raw')
    assert 'foo' in result

@pytest.mark.django_db
def test_handle_inspect(settings_with_galaxy_settings):
    result = call_command('galaxy-settings', 'inspect', '--key', 'foo')
    assert 'bar' in result

@pytest.mark.django_db
def test_handle_update_cache(settings_with_galaxy_settings):
    result = call_command('galaxy-settings', 'update_cache')
    ')
    assert result == 'Cache updated'

@pytest.mark.django_db
def test_handle_clean_cache(settings_with_galaxy_settings):
    result = call_command('galaxy-settings', 'clean_cache')
    assert result == 'Cache cleaned'

@pytest.mark.django_db
def test_handle_allowed_keys(settings_with_dynamic_settings):
    result = call_command('galaxy-settings', 'allowed_keys')
    assert 'foo' in result
    assert 'bar' in result
    assert 'baz' in result

@pytest.mark.django_db
def test_handle_set_invalid_key():
    with pytest.raises(SystemExit):
        call_command('galaxy-settings', 'set', '--key', '', '--value', 'bar')

@pytest.mark.django_db
def test_handle_set_invalid_value():
    with pytest.raises(SystemExit):
        call_command('galaxy-settings', 'set', '--key', 'foo', '--value', '')

@pytest.mark.django_db
def test_handle_get_invalid_key():
    with pytest.raises(SystemExit):
        call_command('galaxy-settings', 'get', '--key', '')

@pytest.mark.django_db
def test_handle_delete_invalid_key():
    with pytest.raises(SystemExit):
        call_command('galaxy-settings', 'delete', '--key', '')

@pytest.mark.django_db
def test_handle_list_invalid_key():
    with pytest.raises(SystemExit):
        call_command('galaxy-settings', 'list', '--key', '')

@pytest.mark.django_db
def test_handle_inspect_invalid_key():
    with pytest.raises(SystemExit):
        call_command('galaxy-settings', 'inspect', '--key', '')

@pytest.mark.django_db
def test_handle_update_cache_invalid():
    with pytest.raises(SystemExit):
        call_command('galaxy-settings', 'update_cache', '--key', '')

@pytest.mark.django_db
def test_handle_clean_cache_invalid():
    with pytest.raises(SystemExit):
        call_command('galaxy-settings', 'clean_cache', '--key', '')

@pytest.mark.django_db
def test_handle_allowed_keys_invalid():
    with pytest.raises(SystemExit):
        call_command('galaxy-settings', 'allowed_keys', '--key', '')
