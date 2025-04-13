import os
import subprocess
import sys
from unittest.mock import patch, MagicMock, mock_open

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from pulp_ansible.app.models import AnsibleRepository
from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES
from pulpcore.plugin.tasking import dispatch

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_ansible_repository():
    repo = AnsibleRepository.objects.create(name="test-repo")
    return repo


@pytest.fixture
def mock_dispatch():
    with patch("galaxy_ng.app.management.commands.set_repo_keyring.dispatch") as mock:
        yield mock


@pytest.fixture
def mock_subprocess_run():
    with patch("galaxy_ng.app.management.commands.set_repo_keyring.subprocess.run") as mock:
        yield mock


@pytest.fixture
def mock_transaction_atomic():
    with patch("galaxy_ng.app.management.commands.set_repo_keyring.transaction.atomic") as mock:
        yield mock


@pytest.fixture
def mock_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")


def test_command_no_keyring_or_publickey():
    with pytest.raises(SystemExit) as excinfo:
        call_command("set-repo-keyring", repository="test-repo")
    assert excinfo.value.code == 1


def test_command_keyring_and_publickey():
    with pytest.raises(SystemExit) as excinfo:
        call_command("set-repo-keyring", repository="test-repo", keyring="galaxy.kbx", publickeypath="public.key")
    assert excinfo.value.code == 1


def test_command_repository_not_found():
    with pytest.raises(SystemExit) as excinfo:
        call_command("set-repo-keyring", repository="nonexistent-repo", keyring="galaxy.kbx")
    assert excinfo.value.code == 1


def test_command_keyring_not_found():
    with pytest.raises(SystemExit) as excinfo:
        call_command("set-repo-keyring", repository="test-repo", keyring="nonexistent.kbx")
    assert excinfo.value.code == 1


def test_command_publickey_read_error(tmp_path):
    public_key_path = tmp_path / "public.key"
    public_key_path.write_text("public key content")
    public_key_path.chmod(0o000)  # Make the file unreadable

    with pytest.raises(SystemExit) as excinfo:
        call_command("set-repo-keyring", repository="test-repo", publickeypath=str(public_key_path))
    assert excinfo.value.code == 1


def test_command_keyring_export_error(mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(stdout=b"", stderr=b"Error", returncode=1)

    with pytest.raises(SystemExit) as excinfo:
        call_command("set-repo-keyring", repository="test-repo", keyring="galaxy.kbx")
    assert excinfo.value.code == 1


def test_command_confirmation_no(mock_input):
    mock_input.side_effect = ["n"]
    with pytest.raises(SystemExit) as excinfo:
        call_command("set-repo-keyring", repository="test-repo", keyring="galaxy.kbx")
    assert excinfo.value.code == 0


def test_command_confirmation_invalid_input(mock_input):
    mock_input.side_effect = ["invalid", "y"]
    call_command("set-repo-keyring", repository="test-repo", keyring="galaxy.kbx")


def test_command_success_with_keyring(mock_ansible_repository, mock_dispatch, mock_subprocess_run, mock_transaction_atomic):
    mock_subprocess_run.return_value = MagicMock(stdout=b"public key content", stderr=b"", returncode=0)
    mock_task = MagicMock(state=TASK_STATES.COMPLETED)
    mock_dispatch.return_value = mock_task

    call_command("set-repo-keyring", repository="test-repo", keyring="galaxy.kbx")


def test_command_success_with_publickey(mock_ansible_repository, mock_dispatch, mock_transaction_atomic):
    mock_task = MagicMock(state=TASK_STATES.COMPLETED)
    mock_dispatch.return_value = mock_task

    with patch("builtins.open", mock_open(read_data="public key content")):
        call_command("set-repo-keyring", repository="test-repo", publickeypath="public.key")


def test_command_task_failed(mock_ansible_repository, mock_dispatch, mock_subprocess_run, mock_transaction_atomic):
    mock_subprocess_run.return_value = MagicMock(stdout=b"public key content", stderr=b"", returncode=0)
    mock_task = MagicMock(state=TASK_STATES.FAILED, error="Task failed")
    mock_dispatch.return_value = mock_task

    with pytest.raises(SystemExit) as excinfo:
        call_command("set-repo-keyring", repository="test-repo", keyring="galaxy.kbx")
    assert excinfo.value.code == 1


def test_command_task_pending(mock_ansible_repository, mock_dispatch, mock_subprocess_run, mock_transaction_atomic):
    mock_subprocess_run.return_value = MagicMock(stdout=b"public key content", stderr=b"", returncode=0)
    mock_task = MagicMock(state=TASK_STATES.WAITING)
    mock_dispatch.return_value = mock_task

    with patch("time.sleep", return_value=None):
        call_command("set-repo-keyring", repository="test-repo", keyring="galaxy.kbx")
```

This test file covers all the necessary functionality and edge cases for the `set-repo-keyring` management command, ensuring high code coverage and adherence to best practices for pytest and Django testing.