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
import sys
from unittest.mock import patch, MagicMock, mock_open

import pytest
from django.core.management.base import CommandError
from django.db import transaction
from pulp_ansible.app.models import AnsibleRepository
from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES
from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app.management.commands.set_repo_keyring import Command, set_repo_gpgkey

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_ansible_repository():
    repo = AnsibleRepository.objects.create(name="test-repo")
    return repo


@pytest.fixture
def mock_task():
    mock_task = MagicMock()
    mock_task.state = TASK_STATES.WAITING
    mock_task.error = None

    def refresh_from_db():
        if mock_task.state == TASK_STATES.WAITING:
            mock_task.state = TASK_STATES.COMPLETED

    mock_task.refresh_from_db = refresh_from_db
    return mock_task


@pytest.fixture
def mock_dispatch(monkeypatch, mock_task):
    monkeypatch.setattr(dispatch, "dispatch", MagicMock(return_value=mock_task))


@pytest.fixture
def mock_subprocess(monkeypatch):
    mock_run = MagicMock()
    mock_run.return_value.stdout = b"mocked-public-key"
    mock_run.return_value.stderr = b""
    monkeypatch.setattr(subprocess, "run", mock_run)


@pytest.fixture
def mock_input(monkeypatch):
    mock_input = MagicMock(return_value="y")
    monkeypatch.setattr(builtins, "input", mock_input)


@pytest.fixture
def mock_open_file(monkeypatch):
    mock_file = mock_open(read_data="mocked-public-key")
    monkeypatch.setattr(builtins, "open", mock_file)


@pytest.fixture
def command():
    return Command()


def test_add_arguments(command):
    parser = MagicMock()
    command.add_arguments(parser)
    parser.add_argument.assert_any_call("--keyring", type=str, help="Keyring", required=False, default="")
    parser.add_argument.assert_any_call(
        "--publickeypath", type=str, help="Path to Public Key File", required=False, default=""
    )
    parser.add_argument.assert_any_call("--repository", type=str, help="Repository name", required=True)
    parser.add_argument.assert_any_call(
        "-y", "--yes", action="store_true", help="Skip confirmation", default=False, required=False
    )


def test_handle_no_keyring_or_publickey(command, capsys):
    with pytest.raises(SystemExit) as excinfo:
        command.handle(repository="test-repo")
    captured = capsys.readouterr()
    assert captured.out == "One of keyring or publickey is required\n"
    assert excinfo.value.code == 1


def test_handle_keyring_and_publickey(command, capsys):
    with pytest.raises(SystemExit) as excinfo:
        command.handle(repository="test-repo", keyring="test.kbx", publickeypath="test.pub")
    captured = capsys.readouterr()
    assert captured.out == "keyring or publickey are mutually exclusive\n"
    assert excinfo.value.code == 1


def test_handle_repository_not_found(command, capsys):
    with pytest.raises(SystemExit) as excinfo:
        command.handle(repository="nonexistent-repo", keyring="test.kbx")
    captured = capsys.readouterr()
    assert captured.out == "Repository nonexistent-repo does not exist\n"
    assert excinfo.value.code == 1


def test_handle_keyring_not_found(command, capsys, mock_ansible_repository):
    with pytest.raises(SystemExit) as excinfo:
        command.handle(repository="test-repo", keyring="nonexistent.kbx")
    captured = capsys.readouterr()
    assert captured.out == "Keyring /etc/pulp/certs/nonexistent.kbx does not exist\n"
    assert excinfo.value.code == 1


def test_handle_publickey(command, mock_ansible_repository, mock_dispatch, mock_open_file, capsys):
    command.handle(repository="test-repo", publickeypath="test.pub", yes=True)
    captured = capsys.readouterr()
    assert captured.out == "Process COMPLETED\nKeyring test.pub set successfully to test-repo repository\n"


def test_handle_keyring(command, mock_ansible_repository, mock_dispatch, mock_subprocess, mock_input, capsys):
    command.handle(repository="test-repo", keyring="test.kbx", yes=False)
    captured = capsys.readouterr()
    assert captured.out == "Process COMPLETED\nKeyring test.kbx set successfully to test-repo repository\n"


def test_handle_keyring_cancel(command, mock_ansible_repository, mock_dispatch, mock_subprocess, mock_input, capsys):
    mock_input.return_value = "n"
    command.handle(repository="test-repo", keyring="test.kbx", yes=False)
    captured = capsys.readouterr()
    assert captured.out == "Process canceled.\n"


def test_handle_task_failed(command, mock_ansible_repository, mock_dispatch, mock_subprocess, mock_input, capsys, monkeypatch):
    mock_task.state = TASK_STATES.FAILED
    mock_task.error = "Mocked error"
    monkeypatch.setattr(dispatch, "dispatch", MagicMock(return_value=mock_task))
    with pytest.raises(SystemExit) as excinfo:
        command.handle(repository="test-repo", keyring="test.kbx", yes=True)
    captured = capsys.readouterr()
    assert captured.out == "Process FAILED\nTask failed with error: Mocked error\n"
    assert excinfo.value.code == 1


def test_set_repo_gpgkey(mock_ansible_repository):
    repo_id = mock_ansible_repository.pk
    gpgkey = "mocked-public-key"
    set_repo_gpgkey(repo_id, gpgkey)
    repo = AnsibleRepository.objects.get(pk=repo_id)
    assert repo.gpgkey == gpgkey


def test_set_repo_gpgkey_transaction_rollback(mock_ansible_repository, monkeypatch):
    repo_id = mock_ansible_repository.pk
    gpgkey = "mocked-public-key"
    mock_save = MagicMock(side_effect=Exception("Mocked exception"))
    monkeypatch.setattr(AnsibleRepository, "save", mock_save)
    with pytest.raises(Exception) as excinfo:
        with transaction.atomic():
            set_repo_gpgkey(repo_id, gpgkey)
    assert str(excinfo.value) == "Mocked exception"
    repo = AnsibleRepository.objects.get(pk=repo_id)
    assert repo.gpgkey != gpgkey
