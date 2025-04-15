import os
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
# Add project root to path if needed
project_root = os.path.abspath(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

import pytest
from unittest import mock
from galaxy_ng.app.management.commands.sync_galaxy_collections import Command
from galaxy_ng.app.utils.galaxy import upstream_collection_iterator
from galaxy_ng.app.utils.legacy import process_namespace
from pulp_ansible.app.models import CollectionVersion
from pulp_ansible.app.models import CollectionRemote
from pulp_ansible.app.models import AnsibleRepository
from pulp_ansible.app.tasks.collections import sync
from pulp_ansible.app.tasks.collections import rebuild_repository_collection_versions_metadata
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES

@pytest.fixture
def mock_upstream_collection_iterator():
    def mock_iterator(*args, **kwargs):
        return [
            {
                'name': 'namespace1',
                'namespace': {'name': 'namespace1'},
                'collection_info': {'name': 'collection1', 'namespace': {'name': 'namespace1'}},
                'collection_versions': [{'version': '1.0'}]
            },
            {
                'name': 'namespace2',
                'namespace': {'name': 'namespace2'},
                'collection_info': {'name': 'collection2', 'namespace': {'name': 'namespace2'}},
                'collection_versions': [{'version': '2.0'}]
            }
        ]
    return mock.patch('galaxy_ng.app.utils.galaxy.upstream_collection_iterator', mock_iterator)

@pytest.fixture
def mock_process_namespace():
    def mock_process(namespace):
        pass
    return mock.patch('galaxy_ng.app.utils.legacy.process_namespace', mock_process)

@pytest.fixture
def mock_dispatch():
    def mock_dispatch(task, kwargs, exclusive_resources=None):
        return mock.Mock()
    return mock.patch('pulpcore.plugin.tasking.dispatch', mock_dispatch)

@pytest.fixture
def mock_collection_version():
    def mock_collection_version():
        return mock.Mock()
    return mock.patch('pulp_ansible.app.models.CollectionVersion', mock_collection_version)

@pytest.fixture
def mock_collection_remote():
    def mock_collection_remote():
        return mock.Mock()
    return mock.patch('pulp_ansible.app.models.CollectionRemote', mock_collection_remote)

@pytest.fixture
def mock_ansible_repository():
    def mock_ansible_repository():
        return mock.Mock()
    return mock.patch('pulp_ansible.app.models.AnsibleRepository', mock_ansible_repository)

class TestCommand:
    def test_handle(self, mock_upstream_collection_iterator, mock_process_namespace, mock_dispatch, mock_collection_version, mock_collection_remote, mock_ansible_repository):
        command = Command()
        command.handle(baseurl='https://example.com', namespace='namespace1', name='collection1', remote='remote1', repository='repository1')
        mock_upstream_collection_iterator.assert_called_once_with(baseurl='https://example.com', collection_namespace='namespace1', collection_name='collection1', limit=None)
        mock_process_namespace.assert_called_once_with('namespace1', {'name': 'namespace1'})
        mock_dispatch.assert_called_once_with(sync, kwargs={'remote_pk': 'remote1.pk', 'repository_pk': 'repository1.pk', 'mirror': False, 'optimize': False}, exclusive_resources=['repository1'])

    def test_handle_rebuild_only(self, mock_upstream_collection_iterator, mock_process_namespace, mock_dispatch, mock_collection_version, mock_collection_remote, mock_ansible_repository):
        command = Command()
        command.handle(baseurl='https://example.com', namespace='namespace1', name='collection1', remote='remote1', repository='repository1', rebuild_only=True)
        mock_upstream_collection_iterator.assert_called_once_with(baseurl='https://example.com', collection_namespace='namespace1', collection_name='collection1', limit=None)
        mock_process_namespace.assert_called_once_with('namespace1', {'name': 'namespace1'})
        mock_dispatch.assert_called_once_with(rebuild_repository_collection_versions_metadata, kwargs={'repository_version_pk': 'repository1.latest_version().pk', 'namespace': 'namespace1', 'name': 'collection1'}, exclusive_resources=['repository1'])

    def test_do_sync_dispatch(self, mock_dispatch):
        command = Command()
        command.do_sync_dispatch(mock.Mock(), mock.Mock(), 'namespace1', 'collection1')
        mock_dispatch.assert_called_once_with(sync, kwargs={'remote_pk': 'remote.pk', 'repository_pk': 'repository.pk', 'mirror': False, 'optimize': False}, exclusive_resources=['repository'])

    def test_do_rebuild_dispatch(self, mock_dispatch):
        command = Command()
        command.do_rebuild_dispatch(mock.Mock(), 'namespace1', 'collection1')
        mock_dispatch.assert_called_once_with(rebuild_repository_collection_versions_metadata, kwargs={'repository_version_pk': 'repository.latest_version().pk', 'namespace': 'namespace1', 'name': 'collection1'}, exclusive_resources=['repository'])

    def test_handle_error(self, mock_upstream_collection_iterator, mock_process_namespace, mock_dispatch, mock_collection_version, mock_collection_remote, mock_ansible_repository):
        command = Command()
        mock_upstream_collection_iterator.return_value = []
        command.handle(baseurl='https://example.com', namespace='namespace1', name='collection1', remote='remote1', repository='repository1')
        mock_upstream_collection_iterator.assert_called_once_with(baseurl='https://example.com', collection_namespace='namespace1', collection_name='collection1', limit=None)
        mock_process_namespace.assert_called_once_with('namespace1', {'name': 'namespace1'})
        mock_dispatch.assert_called_once_with(sync, kwargs={'remote_pk': 'remote1.pk', 'repository_pk': 'repository1.pk', 'mirror': False, 'optimize': False}, exclusive_resources=['repository1'])
