import sys

# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")
from django.conf import settingsimport pytest
import os
import sys
import logging
import yaml
import sys
import time
from unittest.mock import patch, MagicMock, call

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from galaxy_ng.app.utils.galaxy import upstream_collection_iterator
from galaxy_ng.app.utils.legacy import process_namespace

from pulp_ansible.app.models import CollectionVersion, CollectionRemote, AnsibleRepository
from pulp_ansible.app.tasks.collections import sync, rebuild_repository_collection_versions_metadata

from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES

User = get_user_model()

@pytest.fixture
def mock_logger():
    with patch('galaxy_ng.app.management.commands.sync_galaxy_collections.logger') as mock_logger:
        yield mock_logger

@pytest.fixture
def mock_dispatch():
    with patch('galaxy_ng.app.management.commands.sync_galaxy_collections.dispatch') as mock_dispatch:
        yield mock_dispatch

@pytest.fixture
def mock_upstream_collection_iterator():
    with patch('galaxy_ng.app.management.commands.sync_galaxy_collections.upstream_collection_iterator') as mock_iterator:
        yield mock_iterator

@pytest.fixture
def mock_process_namespace():
    with patch('galaxy_ng.app.management.commands.sync_galaxy_collections.process_namespace') as mock_process_namespace:
        yield mock_process_namespace

@pytest.fixture
def mock_collection_remote():
    remote = MagicMock(spec=CollectionRemote)
    remote.pk = 'remote_pk'
    remote.requirements_file = None
    remote.save = MagicMock()
    return remote

@pytest.fixture
def mock_ansible_repository():
    repo = MagicMock(spec=AnsibleRepository)
    repo.pk = 'repo_pk'
    repo.latest_version = MagicMock(return_value=MagicMock(pk='repo_version_pk'))
    return repo

@pytest.fixture
def mock_collection_version():
    cv = MagicMock(spec=CollectionVersion)
    cv.pk = 'cv_pk'
    cv.contents = []
    cv.requires_ansible = None
    return cv

@pytest.fixture
def mock_task():
    task = MagicMock()
    task.state = TASK_STATES.WAITING
    task.error = 'Task failed'
    task.refresh_from_db = MagicMock()
    return task

@pytest.mark.django_db
class TestSyncGalaxyCollectionsCommand:
    def test_handle_no_remote(self, mock_logger, mock_collection_remote, mock_ansible_repository):
        mock_collection_remote.objects.filter.return_value.first.return_value = None
        with pytest.raises(Exception) as excinfo:
            call_command('sync_galaxy_collections', remote='nonexistent')
        assert str(excinfo.value) == 'could not find remote'
        mock_logger.info.assert_called_once()

    def test_handle_no_repository(self, mock_logger, mock_collection_remote, mock_ansible_repository):
        mock_collection_remote.objects.filter.return_value.first.return_value = mock_collection_remote
        mock_ansible_repository.objects.filter.return_value.first.return_value = None
        with pytest.raises(Exception) as excinfo:
            call_command('sync_galaxy_collections', repository='nonexistent')
        assert str(excinfo.value) == 'could not find repo'
        mock_logger.info.assert_called_once()

    def test_handle_with_namespace_and_name(
        self,
        mock_logger,
        mock_dispatch,
        mock_upstream_collection_iterator,
        mock_process_namespace,
        mock_collection_remote,
        mock_ansible_repository,
        mock_collection_version,
        mock_task
    ):
        mock_collection_remote.objects.filter.return_value.first.return_value = mock_collection_remote
        mock_ansible_repository.objects.filter.return_value.first.return_value = mock_ansible_repository
        mock_upstream_collection_iterator.return_value = [
            (
                {'name': 'namespace1'},
                {'namespace': {'name': 'namespace1'}, 'name': 'collection1'},
                [{'version': '1.0.0'}]
            )
        ]
        mock_collection_version.objects.filter.return_value.first.return_value = None
        mock_dispatch.return_value = mock_task

        call_command('sync_galaxy_collections', namespace='namespace1', name='collection1')

        mock_process_namespace.assert_called_once_with('namespace1', {'name': 'namespace1'})
        mock_logger.info.assert_called()
        mock_dispatch.assert_has_calls([
            call(
                sync,
                kwargs={
                    'remote_pk': 'remote_pk',
                    'repository_pk': 'repo_pk',
                    'mirror': False,
                    'optimize': False,
                },
                exclusive_resources=[mock_ansible_repository],
            ),
            call(
                rebuild_repository_collection_versions_metadata,
                kwargs={
                    'repository_version_pk': 'repo_version_pk',
                    'namespace': 'namespace1',
                    'name': 'collection1'
                },
                exclusive_resources=[mock_ansible_repository],
            )
        ])

    def test_handle_rebuild_only(
        self,
        mock_logger,
        mock_dispatch,
        mock_upstream_collection_iterator,
        mock_process_namespace,
        mock_collection_remote,
        mock_ansible_repository,
        mock_collection_version,
        mock_task
    ):
        mock_collection_remote.objects.filter.return_value.first.return_value = mock_collection_remote
        mock_ansible_repository.objects.filter.return_value.first.return_value = mock_ansible_repository
        mock_upstream_collection_iterator.return_value = [
            (
                {'name': 'namespace1'},
                {'namespace': {'name': 'namespace1'}, 'name': 'collection1'},
                [{'version': '1.0.0'}]
            )
        ]
        mock_collection_version.objects.filter.return_value.first.return_value = mock_collection_version
        mock_dispatch.return_value = mock_task

        call_command('sync_galaxy_collections', namespace='namespace1', name='collection1', rebuild_only=True)

        mock_process_namespace.assert_called_once_with('namespace1', {'name': 'namespace1'})
        mock_logger.info.assert_called()
        mock_dispatch.assert_called_once_with(
            rebuild_repository_collection_versions_metadata,
            kwargs={
                'repository_version_pk': 'repo_version_pk',
                'namespace': 'namespace1',
                'name': 'collection1'
            },
            exclusive_resources=[mock_ansible_repository],
        )

    def test_handle_sync_task_failed(
        self,
        mock_logger,
        mock_dispatch,
        mock_upstream_collection_iterator,
        mock_process_namespace,
        mock_collection_remote,
        mock_ansible_repository,
        mock_collection_version,
        mock_task
    ):
        mock_collection_remote.objects.filter.return_value.first.return_value = mock_collection_remote
        mock_ansible_repository.objects.filter.return_value.first.return_value = mock_ansible_repository
        mock_upstream_collection_iterator.return_value = [
            (
                {'name': 'namespace1'},
                {'namespace': {'name': 'namespace1'}, 'name': 'collection1'},
                [{'version': '1.0.0'}]
            )
        ]
        mock_collection_version.objects.filter.return_value.first.return_value = None
        mock_task.state = TASK_STATES.FAILED
        mock_dispatch.return_value = mock_task

        with pytest.raises(SystemExit) as excinfo:
            call_command('sync_galaxy_collections', namespace='namespace1', name='collection1')
        assert excinfo.value.code == 1
        mock_logger.info.assert_called()
        mock_logger.error.assert_called_once_with('Task failed with error (namespace1.collection1): Task failed')

    def test_handle_rebuild_task_failed(
        self,
        mock_logger,
        mock_dispatch,
        mock_upstream_collection_iterator,
        mock_process_namespace,
        mock_collection_remote,
        mock_ansible_repository,
        mock_collection_version,
        mock_task
    ):
        mock_collection_remote.objects.filter.return_value.first.return_value = mock_collection_remote
        mock_ansible_repository.objects.filter.return_value.first.return_value = mock_ansible_repository
        mock_upstream_collection_iterator.return_value = [
            (
                {'name': 'namespace1'},
                {'namespace': {'name': 'namespace1'}, 'name': 'collection1'},
                [{'version': '1.0.0'}]
            )
        ]
        mock_collection_version.objects.filter.return_value.first.return_value = mock_collection_version
        mock_task.state = TASK_STATES.FAILED
        mock_dispatch.return_value = mock_task

        with pytest.raises(SystemExit) as excinfo:
            call_command('sync_galaxy_collections', namespace='namespace1', name='collection1')
        assert excinfo.value.code == 1
        mock_logger.info.assert_called()
        mock_logger.error.assert_called_once_with('Task failed with error (namespace1.collection1): Task failed')

    def test_handle_with_limit(
        self,
        mock_logger,
        mock_dispatch,
        mock_upstream_collection_iterator,
        mock_process_namespace,
        mock_collection_remote,
        mock_ansible_repository,
        mock_collection_version,
        mock_task
    ):
        mock_collection_remote.objects.filter.return_value.first.return_value = mock_collection_remote
        mock_ansible_repository.objects.filter.return_value.first.return_value = mock_ansible_repository
        mock_upstream_collection_iterator.return_value = [
            (
                {'name': 'namespace1'},
                {'namespace': {'name': 'namespace1'}, 'name': 'collection1'},
                [{'version': '1.0.0'}]
            ),
            (
                {'name': 'namespace2'},
                {'namespace': {'name': 'namespace2'}, 'name': 'collection2'},
                [{'version': '1.0.0'}]
            )
        ]
        mock_collection_version.objects.filter.return_value.first.return_value = None
        mock_dispatch.return_value = mock_task

        call_command('sync_galaxy_collections', limit=1)

        mock_process_namespace.assert_called_once_with('namespace1', {'name': 'namespace1'})
        mock_logger.info.assert_called()
        mock_dispatch.assert_has_calls([
            call(
                sync,
                kwargs={
                    'remote_pk': 'remote_pk',
                    'repository_pk': 'repo_pk',
                    'mirror': False,
                    'optimize': False,
                },
                exclusive_resources=[mock_ansible_repository],
            ),
            call(
                rebuild_repository_collection_versions_metadata,
                kwargs={
                    'repository_version_pk': 'repo_version_pk',
                    'namespace': 'namespace1',
                    'name': 'collection1'
                },
                exclusive_resources=[mock_ansible_repository],
            )
        ])
