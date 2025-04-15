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
from django.core.management import call_command
from galaxy_ng.app.management.commands.set_repo_keyring import Command
from pulp_ansible.app.models import AnsibleRepository
from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES

@pytest.fixture
def repository():
    return AnsibleRepository.objects.create(name='test-repo')

@pytest.fixture
def repository_with_gpgkey():
    repo = AnsibleRepository.objects.create(name='test-repo')
    repo.gpgkey = 'test-gpgkey'
    repo.save()
    return repo

@pytest.fixture
def repository_with_publickey():
    repo = AnsibleRepository.objects.create(name='test-repo')
    repo.publickey = 'test-publickey'
    repo.save()
    return repo

@pytest.fixture
def mock_gpg_export(monkeypatch):
    def mock_export(*args, **kwargs):
        return 'test-gpgkey'
    monkeypatch.setattr('subprocess.run', mock_export)

@pytest.fixture
def mock_gpg_export_with_error(monkeypatch):
    def mock_export(*args, **kwargs):
        raise Exception('Test error')
    monkeypatch.setattr('subprocess.run', mock_export)

class TestSetRepoKeyringCommand:
    def test_handle(self, repository, mock_gpg_export):
        call_command('set_repo_keyring', '--repository', repository.name, '--keyring', 'test-keyring')
        repo = AnsibleRepository.objects.get(name=repository.name)
        assert repo.gpgkey == 'test-gpgkey'

    def test_handle_with_publickey(self, repository_with_publickey, mock_gpg_export):
        call_command('set_repo_keyring', '--repository', repository_with_publickey.name, '--publickeypath', 'test-publickey')
        repo = AnsibleRepository.objects.get(name=repository_with_publickey.name)
        assert repo.publickey == 'test-publickey'

    def test_handle_with_error(self, repository, mock_gpg_export_with_error):
        with pytest.raises(SystemExit):
            call_command('set_repo_keyring', '--repository', repository.name, '--keyring', 'test-keyring')

    def test_handle_with_missing_keyring(self, repository):
        with pytest.raises(SystemExit):
            call_command('set_repo_keyring', '--repository', repository.name)

    def test_handle_with_missing_publickey(self, repository):
        with pytest.raises(SystemExit):
            call_command('set_repo_keyring', '--repository', repository.name, '--publickeypath', 'test-publickey')

    def test_handle_with_both_keyring_and_publickey(self, repository):
        with pytest.raises(SystemExit):
            call_command('set_repo_keyring', '--repository', repository.name, '--keyring', 'test-keyring', '--publickeypath', 'test-publickey')

    def test_handle_with_yes_option(self, repository, mock_gpg_export):
        call_command('set_repo_keyring', '--repository', repository.name, '--keyring', 'test-keyring', '--yes')
        repo = AnsibleRepository.objects.get(name=repository.name)
        assert repo.gpgkey == 'test-gpgkey'

    def test_handle_with_no_option(self, repository, mock_gpg_export):
        with pytest.raises(SystemExit):
            call_command('set_repo_keyring', '--repository', repository.name, '--keyring', 'test-keyring')

class TestSetRepoGPGKey:
    def test_set_repo_gpgkey(self, repository):
        set_repo_gpgkey(repository.pk, 'test-gpgkey')
        repo = AnsibleRepository.objects.get(pk=repository.pk)
        assert repo.gpgkey == 'test-gpgkey'

    def test_set_repo_gpgkey_with_error(self, repository):
        with pytest.raises(Exception):
            set_repo_gpgkey(repository.pk, 'test-gpgkey')
