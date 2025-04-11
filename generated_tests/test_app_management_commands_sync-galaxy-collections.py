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
def test_command_no_remote(mock_logger, mock_collection_remote, mock_ansible_repository, mock_task, mock_dispatch):
    CollectionRemote.objects.all().delete()
    with pytest.raises(Exception) as excinfo:
        call_command('sync_galaxy_collections', remote='nonexistent')
    assert str(excinfo.value) == 'could not find remote'
    mock_logger.error.assert_called_once_with('could not find remote')

@pytest.mark.django_db
def test_command_no_repository(mock_logger, mock_collection_remote, mock_ansible_repository, mock_task, mock_dispatch):
    AnsibleRepository.objects.all().delete()
    with pytest.raises(Exception) as excinfo:
        call_command('sync_galaxy_collections', repository='nonexistent')
    assert str(excinfo.value) == 'could not find repo'
    mock_logger.error.assert_called_once_with('could not find repo')

@pytest.mark.django_db
def test_command_sync_and_rebuild(
    mock_logger,
    mock_dispatch,
    mock_upstream_collection_iterator,
    mock_process_namespace,
    mock_collection_remote,
    mock_ansible_repository,
    mock_collection_version,
    mock_task
):
    CollectionRemote.objects.create(name='published')
    AnsibleRepository.objects.create(name='published')

    mock_upstream_collection_iterator.return_value = [
        (
            {'name': 'namespace1'},
            {'namespace': {'name': 'namespace1'}, 'name': 'collection1'},
            [{'version': '1.0.0'}]
        )
    ]

    mock_collection_version.objects.filter.return_value.first.return_value = None
    mock_dispatch.return_value = mock_task

    call_command('sync_galaxy_collections')

    mock_process_namespace.assert_called_once_with('namespace1', {'name': 'namespace1'})
    mock_logger.info.assert_has_calls([
        call('1. namespace1.collection1 versions:1'),
        call('sync: True'),
        call('rebuild: True'),
        call('dispatching sync for namespace1.collection1'),
        call('Syncing namespace1.collection1 WAITING'),
        call('Syncing namespace1.collection1 COMPLETED'),
        call('dispatching rebuild for namespace1.collection1'),
        call('Rebuild namespace1.collection1 WAITING'),
        call('Rebuild namespace1.collection1 COMPLETED'),
    ])

    mock_dispatch.assert_has_calls([
        call(
            sync,
            kwargs={
                'remote_pk': 'remote_pk',
                'repository_pk': 'repo_pk',
                'mirror': False,
                'optimize': False,
            },
            exclusive_resources=[mock_ansible_repository]
        ),
        call(
            rebuild_repository_collection_versions_metadata,
            kwargs={
                'repository_version_pk': 'repo_version_pk',
                'namespace': 'namespace1',
                'name': 'collection1'
            },
            exclusive_resources=[mock_ansible_repository]
        )
    ])

@pytest.mark.django_db
def test_command_rebuild_only(
    mock_logger,
    mock_dispatch,
    mock_upstream_collection_iterator,
    mock_process_namespace,
    mock_collection_remote,
    mock_ansible_repository,
    mock_collection_version,
    mock_task
):
    CollectionRemote.objects.create(name='published')
    AnsibleRepository.objects.create(name='published')

    mock_upstream_collection_iterator.return_value = [
        (
            {'name': 'namespace1'},
            {'namespace': {'name': 'namespace1'}, 'name': 'collection1'},
            [{'version': '1.0.0'}]
        )
    ]

    mock_collection_version.objects.filter.return_value.first.return_value = mock_collection_version
    mock_dispatch.return_value = mock_task

    call_command('sync_galaxy_collections', rebuild_only=True)

    mock_process_namespace.assert_called_once_with('namespace1', {'name': 'namespace1'})
    mock_logger.info.assert_has_calls([
        call('1. namespace1.collection1 versions:1'),
        call('sync: False'),
        call('rebuild: True'),
        call('dispatching rebuild for namespace1.collection1'),
        call('Rebuild namespace1.collection1 WAITING'),
        call('Rebuild namespace1.collection1 COMPLETED'),
    ])

    mock_dispatch.assert_called_once_with(
        rebuild_repository_collection_versions_metadata,
        kwargs={
            'repository_version_pk': 'repo_version_pk',
            'namespace': 'namespace1',
            'name': 'collection1'
        },
        exclusive_resources=[mock_ansible_repository]
    )

@pytest.mark.django_db
def test_command_sync_task_failed(
    mock_logger,
    mock_dispatch,
    mock_upstream_collection_iterator,
    mock_process_namespace,
    mock_collection_remote,
    mock_ansible_repository,
    mock_collection_version,
    mock_task
):
    CollectionRemote.objects.create(name='published')
    AnsibleRepository.objects.create(name='published')

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
        call_command('sync_galaxy_collections')

    assert excinfo.value.code == 1
    mock_logger.error.assert_called_once_with('Task failed with error (namespace1.collection1): Task failed')

@pytest.mark.django_db
def test_command_rebuild_task_failed(
    mock_logger,
    mock_dispatch,
    mock_upstream_collection_iterator,
    mock_process_namespace,
    mock_collection_remote,
    mock_ansible_repository,
    mock_collection_version,
    mock_task
):
    CollectionRemote.objects.create(name='published')
    AnsibleRepository.objects.create(name='published')

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
        call_command('sync_galaxy_collections')

    assert excinfo.value.code == 1
    mock_logger.error.assert_called_once_with('Task failed with error (namespace1.collection1): Task failed')

@pytest.mark.django_db
def test_command_limit(
    mock_logger,
    mock_dispatch,
    mock_upstream_collection_iterator,
    mock_process_namespace,
    mock_collection_remote,
    mock_ansible_repository,
    mock_collection_version,
    mock_task
):
    CollectionRemote.objects.create(name='published')
    AnsibleRepository.objects.create(name='published')

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
    mock_logger.info.assert_has_calls([
        call('1. namespace1.collection1 versions:1'),
        call('sync: True'),
        call('rebuild: True'),
        call('dispatching sync for namespace1.collection1'),
        call('Syncing namespace1.collection1 WAITING'),
        call('Syncing namespace1.collection1 COMPLETED'),
        call('dispatching rebuild for namespace1.collection1'),
        call('Rebuild namespace1.collection1 WAITING'),
        call('Rebuild namespace1.collection1 COMPLETED'),
    ])

    mock_dispatch.assert_has_calls([
        call(
            sync,
            kwargs={
                'remote_pk': 'remote_pk',
                'repository_pk': 'repo_pk',
                'mirror': False,
                'optimize': False,
            },
            exclusive_resources=[mock_ansible_repository]
        ),
        call(
            rebuild_repository_collection_versions_metadata,
            kwargs={
                'repository_version_pk': 'repo_version_pk',
                'namespace': 'namespace1',
                'name': 'collection1'
            },
            exclusive_resources=[mock_ansible_repository]
        )
    ])
