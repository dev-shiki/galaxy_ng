import sys

# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")
from django.conf import settingsimport pytest
import os
import sys
Okay, I need to write comprehensive pytest tests for the set-repo-keyring command in the Galaxy NG project. Let me start by understanding the code provided.

The command is a Django management command that sets a GPG keyring for an Ansible repository. The main steps are parsing arguments, checking if the repository exists, handling keyring or public key inputs, possibly exporting the public key from a keyring, dispatching a task to set the GPG key, and waiting for the task result.

First, I'll need to create tests for the Command class's handle method. The tests should cover different scenarios like valid inputs, missing arguments, invalid paths, user confirmation, and task outcomes.

I should use pytest fixtures to mock external dependencies like subprocess, os.path.exists, and database interactions. Since Django models are involved, I'll need to use the Django test framework's TestCase or TransactionTestCase, but since it's pytest, maybe use pytest-django's features.

Let me outline the test cases:

1. Test when neither keyring nor publickey is provided. Should exit with error.
2. Test when both keyring and publickey are provided. Should exit with error.
3. Test repository does not exist. Should exit with error.
4. Test publickey file does not exist. Should raise an error when trying to read it.
5. Test keyring path does not exist. Should exit with error.
6. Test when using keyring and user cancels confirmation. Should exit without proceeding.
7. Test when using keyring and user confirms. Should proceed to export the key and dispatch the task.
8. Test task failure. Should report error and exit.
9. Test task success. Should confirm the key was set correctly.

For mocks, I'll need to mock:

- subprocess.run to simulate the gpg command's output.
- os.path.exists to control whether the keyring or public key exists.
- AnsibleRepository.objects.get to return a mock repository or raise DoesNotExist.
- dispatch to return a mock task with a state and error.
- The task's refresh_from_db method.

Also, since the code uses sys.exit, I need to capture that using pytest's exit codes or mock sys.exit.

Wait, in the handle method, after some checks, it calls sys.exit(1) when errors occur. So in tests, I should check that the command exits with the correct code in those cases.

I should structure the tests using pytest fixtures. Maybe a fixture for the command instance, and others for mocks.

Let me think about the structure of the test file. The test file should be in galaxy_ng/tests/unit/app/management/commands/test_set-repo-keyring.py.

Imports needed:

- pytest
- unittest.mock (for MagicMock, patch)
- django.test (maybe TestCase, but with pytest-django, perhaps not needed)
- from django.core.management import call_command
- from django.core.management.base import CommandError
- from pulp_ansible.app.models import AnsibleRepository
- from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES
- from the command module itself.

Wait, the command is in galaxy_ng/app/management/commands/set_repo_keyring.py, so the import would be from galaxy_ng.app.management.commands.set_repo_keyring import Command.

But in the test, I can import the Command class directly.

Now, for each test case:

Test case 1: No keyring or publickey. The code checks if not keyring and not publickey, then exits. So in the test, set both to empty strings. The command should exit with code 1.

Test case 2: Both provided. The code checks if keyring and publickey are both set, then exits. So set both, and check exit code 1.

Test case 3: Repository does not exist. The code tries to get the repository, and if not found, exits with code 1. So mock AnsibleRepository.objects.get to raise DoesNotExist.

Test case 4: Publickey path does not exist. So when publickey is provided, but the file doesn't exist. The code would try to open it, which would raise FileNotFoundError. Wait, in the code, after checking that either keyring or publickey is provided, it proceeds. For publickey case, it opens the file. So if the file doesn't exist, the open would throw an error. But in the code, there's no try-except around that. So in that case, the code would crash. Wait, but in the code, when publickey is provided, it does:

with open(publickey) as pubkeyfile:
    pubkey = pubkeyfile.read()

So if the file doesn't exist, that would raise FileNotFoundError. The code doesn't handle that, so the test should check that the command raises an error here. But how to test that? Maybe in the test, when publickey is given but the path doesn't exist, the code should exit with error. Wait, but the code doesn't have a check for that. So perhaps the test should mock the open to raise an error, and then check that the command exits with code 1?

Hmm, perhaps in the test, when publickey is provided but the file doesn't exist, the code would crash, but the user might expect an error message. Since the code doesn't handle that, maybe the test should check that the code raises an exception here. Alternatively, maybe the code should check if the publickey file exists before opening. But according to the code, it's not doing that. So perhaps that's a bug, but for the test, I need to cover that scenario.

Alternatively, maybe the test should mock the open function to raise FileNotFoundError, and then check that the command exits with an error.

Test case 5: Keyring path does not exist. The code checks if keyring_path exists. If not, it exits with error. So mock os.path.exists to return False, and check that the command exits with code 1.

Test case 6: User cancels confirmation. When using keyring and not --yes, the code asks for confirmation. If the user enters 'n', the process should exit. So mock the input to return 'n', and check that the command returns early (maybe by checking that dispatch wasn't called).

Test case 7: User confirms. Then the code proceeds to run the subprocess, get the pubkey, dispatch the task, and wait. Need to mock subprocess.run to return a successful output, and the task to be successful.

Test case 8: Task fails. The task's state is FAILED, so the command should exit with error.

Test case 9: Task succeeds. The repo's gpgkey should be set to the pubkey.

Now, for fixtures:

- Mock the subprocess module's run function.
- Mock os.path.exists.
- Mock AnsibleRepository.objects.get.
- Mock dispatch to return a mock task.
- Mock the tempdir creation (maybe using mkdtemp).
- Mock the input function for user confirmation.

Also, since the code uses sys.exit, in the tests, when the command is called via call_command, it would raise CommandError if it exits with non-zero. Wait, in Django management commands, if you call sys.exit(1), the call_command function will raise CommandError. So in the tests, when expecting an exit, we can expect that a CommandError is raised with the appropriate message.

Wait, but in the code, after printing an error message, it calls sys.exit(1). So in the test, when using call_command, that should raise a CommandError with the exit code. So in the test, when expecting an error, we can use pytest.raises(CommandError) and check the message.

Alternatively, perhaps the tests should use the command's handle method directly, but that might be more involved. Alternatively, using call_command with the arguments and checking for exceptions.

Hmm, perhaps the best approach is to use the call_command function and check for CommandError exceptions where appropriate.

Now, structuring the test file:

Start with necessary imports:

import os
from unittest.mock import MagicMock, patch, call
from django.core.management import call_command
from django.core.management.base import CommandError
from pulp_ansible.app.models import AnsibleRepository
from galaxy_ng.app.management.commands.set_repo_keyring import Command

Then, define fixtures. For example, a fixture to mock subprocess.run:

@pytest.fixture
def mock_subprocess_run():
    with patch('subprocess.run') as mock_run:
        yield mock_run

Similarly, mock os.path.exists:

@pytest.fixture
def mock_os_path_exists():
    with patch('os.path.exists') as mock_exists:
        yield mock_exists

Also, mock the AnsibleRepository's get method:

@pytest.fixture
def mock_ansible_repo_get():
    with patch('pulp_ansible.app.models.AnsibleRepository.objects.get') as mock_get:
        mock_repo = MagicMock()
        mock_get.return_value = mock_repo
        yield mock_get

Another fixture for the dispatch function:

@pytest.fixture
def mock_dispatch():
    with patch('pulpcore.plugin.tasking.dispatch') as mock_dispatch:
        mock_task = MagicMock()
        mock_dispatch.return_value = mock_task
        yield mock_dispatch

Also, a fixture for the tempdir:

@pytest.fixture
def mock_tempfile_mkdtemp():
    with patch('tempfile.mkdtemp') as mock_mkdtemp:
        mock_mkdtemp.return_value = '/tmp/fake_temp'
        yield mock_mkdtemp

And a fixture for input:

@pytest.fixture
def mock_input():
    with patch('builtins.input') as mock_input:
        yield mock_input

Now, writing the test functions.

Test case 1: No keyring or publickey.

def test_no_keyring_or_publickey(mock_ansible_repo_get, mock_os_path_exists):
    with pytest.raises(CommandError) as exc:
        call_command('set_repo_keyring', '--repository=myrepo')
    assert 'One of keyring or publickey is required' in str(exc.value)

Wait, but the command's handle method uses sys.exit(1), so call_command would raise CommandError with the exit code. The message would be captured in the exception's value?

Hmm, perhaps the error message is printed via self.echo with style.ERROR, but the actual exit is via sys.exit(1). The call_command function would capture that and raise CommandError with the exit code. The message might not be in the exception's value. So maybe the test can't check the message directly here. Alternatively, perhaps the test should check that the command exits with code 1, but in pytest, using call_command, the CommandError's return code can be checked.

Wait, according to Django's documentation, when a management command calls sys.exit(n), call_command will raise CommandError with the exit code as the message. So in the test, the exception's message would be the exit code. So perhaps the message isn't captured here. So maybe this test can't check the message, but can check that the exit code is 1. Alternatively, maybe the code should raise a CommandError instead of sys.exit, but that's part of the code under test. Since the code uses sys.exit, the test can only check that the CommandError is raised, but not the message. Hmm, that complicates things. Maybe the test should instead check that the correct error message is printed. To do that, perhaps capture stdout/stderr.

Alternatively, maybe it's better to test the handle method directly by creating an instance of the Command and calling handle with the options. That way, we can capture the output and check for the error message.

Hmm, perhaps using the command's handle method directly would be better for more control. Let me think.

Alternatively, use the capsys fixture to capture output.

Alternatively, perhaps the tests should be structured to use the command's handle method directly, passing in options, and then checking the outputs and side effects.

But that might require more setup. Let me think of an example.

Alternatively, proceed with the call_command approach but accept that some messages can't be checked directly.

Alternatively, perhaps the code should be refactored to raise CommandError instead of sys.exit, but that's beyond the current task.

Hmm, perhaps for the first test case, the test can check that CommandError is raised, and the exit code is 1. The message might not be accessible, but the test can proceed.

Alternatively, maybe the code's error messages are printed to stderr, so using capsys, we can check that the error message is present.

So, perhaps in the test, after calling call_command and expecting CommandError, we can check the captured stderr.

Let me adjust the test:

def test_no_keyring_or_publickey(mock_ansible_repo_get, mock_os_path_exists, capsys):
    with pytest.raises(CommandError) as exc:
        call_command('set_repo_keyring', '--repository=myrepo')
    captured = capsys.readouterr()
    assert "One of keyring or publickey is required" in captured.err
    assert exc.value.returncode == 1

But this requires capturing the output. So adding capsys as a fixture.

Okay, that's manageable.

Now, moving on to test case 2: both keyring and publickey provided.

def test_both_keyring_and_publickey(mock_ansible_repo_get, mock_os_path_exists, capsys):
    with pytest.raises(CommandError) as exc:
        call_command('set_repo_keyring', '--repository=myrepo', '--keyring=kb', '--publickeypath=pk')
    captured = capsys.readouterr()
    assert "keyring or publickey are mutually exclusive" in captured.err
    assert exc.value.returncode == 1

Test case 3: repository does not exist.

def test_repository_does_not_exist(mock_ansible_repo_get, mock_os_path_exists):
    mock_ansible_repo_get.side_effect = AnsibleRepository.DoesNotExist
