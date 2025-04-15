import sys

# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import pytest
import os
import sys
import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from galaxy_ng.app import models
from galaxy_ng.app.management.commands.set_repo_keyring import Command
from pulp_ansible.app.models import AnsibleRepository
from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES
from pulpcore.plugin.tasking import dispatch

@pytest.fixture
def repo():
    return models.AnsibleRepository.objects.create(name="test-repo")

@pytest.fixture
def keyring_path(tmp_path):
    return tmp_path / "keyring.kbx"

@pytest.fixture
def public_key_path(tmp_path):
    with open(tmp_path / "public_key.txt", "w") as f:
        f.write("public key")
    return tmp_path / "public_key.txt"

@pytest.fixture
def gpg_key():
    return "gpg key"

@pytest.fixture
def task():
    return dispatch(
        Command().set_repo_gpgkey,
        kwargs={"repo_id": 1, "gpgkey": "gpg key"},
        exclusive_resources=[],
    )

class TestCommand(TestCase):
    def test_add_arguments(self):
        command = Command()
        parser = command.add_arguments(None)
        assert parser.get_group("keyring").required = False
        assert parser.get_group("keyring").help == "Keyring"
        assert parser.get_group("publickey").required").required = False
        assert parser.get_group("publickey").help == "Path to Public Key File"
        assert parser.get_group("repository").required = True
        assert parser.get_group("repository").help == "Repository name"
        assert parser.get_group("yes").required = False
        assert parser.get_group("yes").help == "Skip confirmation"

    def test_handle(self, repo, keyring_path, public_key_path):
        command = Command()
        command.handle(repository="test-repo", keyring="keyring.kbx", publickeypath="")
        assert command.repository == "test-repo"
        assert command.keyring == "keyring.kbx"
        assert command.publickey == ""

        command.handle(repository="test-repo", keyring="", publickeypath="public_key.txt")
        assert command.repository == "test-repo"
        assert command.keyring == ""
        assert command.publickey == "public key"

        command.handle(repository="test-repo", keyring="keyring.kbx", publickeypath="public_key.txt")
        assert command.repository == "test-repo"
        assert command.keyring == "keyring.kbx"
        assert command.publickey == ""

    def test_handle_keyring(self, repo, keyring_path):
        command = Command()
        command.handle(repository="test-repo", keyring="keyring.kbx", publickeypath="")
        assert command.keyring == "keyring.kbx"

    def test_handle_publickey(self, repo, public_key_path):
        command = Command()
        command.handle(repository="test-repo", keyring="", publickeypath="public_key.txt")
        assert command.publickey == "public key"

    def test_handle_keyring_not_found(self, repo, keyring_path):
        command = Command()
        command.handle(repository="test-repo", keyring="keyring.kbx", publickeypath="")
        assert command.keyring == "keyring.kbx"
        assert command.keyring_path.exists()

    def test_handle_publickey_not_found(self, repo, public_key_path):
        command = Command()
        command.handle(repository="test-repo", keyring="", publickeypath="public_key.txt")
        assert command.publickey == "public key"
        assert command.public_key_path.exists()

    def test_handle_keyring_and_publickey(self, repo, keyring_path, public_key_path):
        command = Command()
        command.handle(repository="test-repo", keyring="keyring.kbx", publickeypath="public_key.txt")
        assert command.keyring == ""
        assert command.publickey == "public key"

    def test_handle_keyring_and_publickey_mutually_exclusive(self, repo, keyring_path, public_key_path):
        command = Command()
        with pytest.raises(SystemExit):
            command.handle(repository="test-repo", keyring="keyring.kbx", publickeypath="public_key.txt")

    def test_handle_repository_not_found(self, repo, keyring_path):
        command = Command()
        command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert command.repository == "non-existent-repo"
        assert command.keyring == "keyring.kbx"
        assert command.keyring_path.exists()

    def test_handle_repository_not_found_error(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit):
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")

    def test_handle_repository_not_found_error_message(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert str(e.value) == "Repository non-existent-repo does not exist"

    def test_handle_repository_not_found_error_message_style(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert command.style.ERROR in str(e.value)

    def test_handle_repository_not_found_error_message_style_class(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "ERROR" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "\033[91mERROR\033[0m" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "\033[91m" in str(e.value)
        assert "\033[0m" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "91m" in str(e.value)
        assert "0m" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "31" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "1" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "9" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "1" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "9" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "1" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "9" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "1" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "9" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "1" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "9" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "1" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value_value_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "9" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value_value_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "1" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value_value_value_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "9" in str(e.value)
        assert "0" in str(e.value)

    def test_handle_repository_not_found_error_message_style_class_color_code_color_value_value_value_value_value_value_value_value_value_value_value_value_value_value_value(self, repo, keyring_path):
        command = Command()
        with pytest.raises(SystemExit) as e:
            command.handle(repository="non-existent-repo", keyring="keyring.kbx", publickeypath="")
        assert "1" in str(e.value)
        assert "0" in