Okay, I need to write comprehensive pytest tests for the galaxy-settings management command in the Galaxy NG project. Let me start by understanding the code structure and what each part does.

The command has several subcommands: set, get, delete, list, inspect, update_cache, clean_cache, allowed_keys. Each of these has different parameters and functionalities. The tests should cover all these subcommands and their edge cases.

First, I'll need to set up the test file structure. The tests should be in galaxy_ng/tests/unit/app/management/commands/test_galaxy-settings.py. I'll start by importing necessary modules like pytest, mock, and the command class. Also, since it's a Django test, I should use Django's TestCase or TransactionTestCase, but since we're dealing with management commands, maybe the LiveServerTestCase isn't needed here. Wait, perhaps using the call_command function from Django's test utils would be better.

Wait, the management command is a BaseCommand, so to test it, I can use the call_command function. But since some methods interact with the database, I should use the Django test framework's TestCase. Also, since some methods involve database operations, I'll need to mock certain parts to avoid hitting the real database, unless testing the actual DB interactions.

Wait, but for some tests, like testing the actual database operations, maybe we need to use the database. Hmm, but for unit tests, perhaps mocking is better. Let me think.

The Setting model is part of the code, so I'll need to mock its methods like set_value_in_db, get_value_from_db, delete_all_versions, etc. Also, the Setting.objects.all().delete() in handle_delete when --all is used. So mocking the Setting model's methods would be necessary to avoid actual DB hits.

Also, the dynaconf's upperfy function is used, which converts keys to uppercase. So when testing, the key passed to the command should be uppercased in the mock calls.

The tests should cover all subcommands. Let's list them:

1. set: tests for setting a key with and without is_secret. Need to mock Setting.set_value_in_db and check that it's called with the right parameters.

2. get: test getting a key, with and without raw, and default. Need to mock get_value_from_db and get, and handle exceptions like DoesNotExist.

3. delete: test deleting a key with all_versions, deleting latest version, and deleting all settings. Also, when key is not provided, but all is set. Also, when neither key nor all is provided, but according to the code, the delete subcommand requires either key or all. Wait, looking at the code for delete_parser: the --key is not required, but --all is a flag. So if --all is set, it deletes all. Otherwise, if key is provided, delete that key with or without all_versions. But if neither is given, the code would proceed to the with suppress block, which would not delete anything, and return "Nothing to delete".

So tests for delete should cover all these scenarios.

4. list: test raw and non-raw modes. Mock as_dict and get.

5. inspect: mock get_history from dynaconf.utils.inspect.

6. update_cache and clean_cache: mock Setting.update_cache and Setting.clean_cache.

7. allowed_keys: mock DYNAMIC_SETTINGS_SCHEMA.keys().

Also, edge cases like invalid keys, missing parameters, etc. For example, in 'get', if the key doesn't exist and default is provided, it should return the default. If raw is True and the key doesn't exist, return default.

Another edge case: when using 'delete' with --all and --key, but according to the code, if --all is set, it ignores the key. So need to test that.

Also, in handle_delete, if all_settings is True (from --all), then it deletes all settings and returns the result (number of objects deleted). But in the code, the return is Setting.objects.all().delete(), which returns (count, detail). So the test should check that the mock is called correctly.

Now, for fixtures and mocks:

- Use pytest's monkeypatch to mock the Setting model's methods.

- Use mock.patch to mock the Setting class and its methods.

Wait, perhaps using the @mock.patch decorator to patch the Setting class and its methods. Alternatively, since the code uses from galaxy_ng.app.models.config import Setting, we can patch the Setting class in the module under test.

Wait, the command is in galaxy_ng/app/management/commands/galaxy-settings.py, so when testing, the imports in that module would be from galaxy_ng.app.models.config import Setting. So to mock Setting, we can patch 'galaxy_ng.app.management.commands.galaxy_settings.Setting' (the module path where the command is located). Wait, the actual module name is galaxy_settings (since the file is galaxy-settings.py, but in Python, the module name would be galaxy_settings). So the correct path would be 'galaxy_ng.app.management.commands.galaxy_settings.Setting'.

Alternatively, perhaps better to use autospec=True when patching to ensure that the mocked methods exist.

Also, for the dynaconf's upperfy function, since it's imported as from dynaconf.utils import upperfy, we can mock that function as well if needed, but in most cases, since the code calls upperfy(key), which converts the key to uppercase, perhaps in the tests, we can just ensure that the key passed to the Setting methods is uppercased.

Wait, in handle_set, the key is passed as is, but in handle_get, the key is uppercased via upperfy(key). So when testing, the mock for Setting.get_value_from_db should be called with uppercased key.

So, for example, if the user runs 'get --key=FOO', the code would call upperfy('FOO') which is 'FOO', but if the key is 'foo', it becomes 'FOO'.

Therefore, in tests, when passing a key like 'test_key', the mock should expect uppercased versions.

Now, structuring the test file:

The test file should start with necessary imports:

import pytest
from unittest import mock
from django.core.management import call_command
from django.core.management.base import CommandError
from galaxy_ng.app.management.commands.galaxy_settings import Command

Wait, but the actual module is named galaxy_settings (since the file is galaxy-settings.py, which becomes galaxy_settings in Python). So the import would be from galaxy_ng.app.management.commands.galaxy_settings import Command.

Wait, the code in the module is:

class Command(BaseCommand):
    ...

So the Command class is in that module. So the import is correct.

Now, for each subcommand, I can write test functions. Since pytest allows parametrization, but for clarity, perhaps separate test functions for each subcommand.

But first, let's think about the setup. Since some tests require mocking the Setting model's methods, perhaps using a fixture that patches the Setting class.

Wait, perhaps using a fixture that patches the Setting class and returns a MagicMock instance. For example:

@pytest.fixture
def mock_setting(mocker):
    mock_setting = mocker.patch('galaxy_ng.app.management.commands.galaxy_settings.Setting')
    return mock_setting

Then, in each test, we can use this mock_setting fixture to set up the mocks.

Alternatively, each test can patch the Setting class as needed.

Alternatively, for each test, we can use mocker.patch to mock the Setting class and its methods.

Hmm, perhaps using the mock_setting fixture would be better for reusability.

Wait, but each test may need different setups. Let's see.

Let me start writing the test functions.

First, the test for the 'set' subcommand.

Test 'set' command:

def test_handle_set(mocker):
    # Arrange
    mock_setting = mocker.patch('galaxy_ng.app.management.commands.galaxy_settings.Setting')
    cmd = Command()
    options = {'key': 'TEST_KEY', 'value': 'test_value', 'is_secret': True}
    
    # Act
    result = cmd.handle_set(**options)
    
    # Assert
    mock_setting.set_value_in_db.assert_called_once_with('TEST_KEY', 'test_value', is_secret=True)
    assert result == mock_setting.set_value_in_db.return_value

Wait, but the key is passed as 'TEST_KEY', which is already uppercase, so upperfy is not needed here. But in the code, the key is passed as is. Wait, in handle_set, the key is taken from options['key'], which is the user input. So if the user inputs 'test_key', the code would pass that to Setting.set_value_in_db. But in the code, the key is not uppercased here. Wait, looking at the code for handle_set:

def handle_set(self, *args, **options):
    key = options['key']
    value = options['value']
    is_secret = options['is_secret']
    return Setting.set_value_in_db(key, value, is_secret=is_secret)

Ah, so the key is not uppercased here. Wait, but in the get command, the key is uppercased via upperfy. So in the set command, the key is stored as the user provided it? Or is there a convention that keys are stored in uppercase?

Wait, the upperfy function converts the key to uppercase. So perhaps the Setting model expects keys to be in uppercase. Therefore, in the set command, the key should be uppercased before storing. But according to the code, the handle_set does not uppercase the key. That might be a problem. Wait, but maybe the Setting model's set_value_in_db method handles that. Or perhaps the code is incorrect here. Hmm, but since this is a test for the command, perhaps the test should ensure that the key is passed as is, and the model's method is responsible for handling it.

Alternatively, maybe the code in handle_set is wrong, but since we are testing the command, we can proceed as per the code's current state.

So in the test, when the user provides a key like 'test_key', the command passes it as is to Setting.set_value_in_db. So the test should check that the key is passed as 'test_key' (unless the code is supposed to uppercase it, but according to the code, it's not).

Wait, but in the get command, the key is uppercased via upperfy. So perhaps the keys are stored in uppercase, so the set command should uppercase the key. But according to the code, it's not. That might be a bug, but since we are writing tests for the existing code, we have to test as per the current code.

Therefore, in the test for 'set', the key is passed as given, so the mock should expect the key as provided.

Another test case for 'set' without is_secret:

def test_handle_set_without_secret(mocker):
    mock_setting = mocker.patch('galaxy_ng.app.management.commands.galaxy_settings.Setting')
    cmd = Command()
    options = {'key': 'TEST_KEY', 'value': 'test_value', 'is_secret': False}
    result = cmd.handle_set(**options)
    mock_setting.set_value_in_db.assert_called_once_with('TEST_KEY', 'test_value', is_secret=False)
    assert result == mock_setting.set_value_in_db.return_value

Now, moving to 'get' command.

Test 'get' with raw=True and key exists:

def test_handle_get_raw_exists(mocker):
    mock_setting = mocker.patch('galaxy_ng.app.management.commands.galaxy_settings.Setting')
    mock_setting.get_value_from_db.return_value = 'test_value'
    cmd = Command()
    options = {'key': 'test_key', 'raw': True, 'default': 'default'}
    result = cmd.handle_get(**options)
    mock_setting.get_value_from_db.assert_called_once_with(upperfy('test_key'))
    assert result == 'test_value'

Test 'get' with raw=True and key does not exist, returns default:

def test_handle_get_raw_not_exists(mocker):
    mock_setting = mocker.patch('galaxy_ng.app.management.commands.galaxy_settings.Setting')
    mock_setting.get_value_from_db.side_effect = Setting.DoesNotExist
    cmd = Command()
    options = {'key': 'test_key', 'raw': True, 'default': 'default_value'}
    result = cmd.handle_get(**options)
    assert result == 'default_value'

Test 'get' without raw (so uses Setting.get), which might involve default:

def test_handle_get_non_raw(mocker):
    mock_setting = mocker.patch('galaxy_ng.app.management.commands.galaxy_settings.Setting')
    mock_setting.get.return_value = 'processed_value'
    cmd = Command()
    options = {'key': 'test_key', 'raw': False, 'default': 'default'}
    result = cmd.handle_get(**options)
    mock_setting.get.assert_called_once_with(upperfy('test_key'), default='default')
    assert result == 'processed_value'

Now, the 'delete' command has multiple cases.

Test delete with key and all_versions:

def test_handle_delete_all_versions(mocker):
    mock_setting = mocker.patch('gal