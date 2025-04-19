# Import patch helper
from galaxy_ng.tests.unit.ai_generated.patch_imports import patch_test_imports
patch_test_imports()

import os
import sys
import pytest
import sys
# Import module being tested
try:
    from galaxy_ng.app.management.commands.sync_galaxy_collections import *
except (ImportError, ModuleNotFoundError):
    # Mock module if import fails
    sys.modules['galaxy_ng.app.management.commands.sync_galaxy_collections'] = mock.MagicMock()


from unittest import mock

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

# Use pytest marks for Django database handling
pytestmark = pytest.mark.django_db

# Mock modules accessed in __init__.py
import sys
social_auth = mock.MagicMock()
sys.modules['galaxy_ng.social.auth'] = social_auth

# Mock factories
factories = mock.MagicMock()
factories.UserFactory = mock.MagicMock(return_value=mock.MagicMock(username="test_user"))
factories.GroupFactory = mock.MagicMock()
factories.NamespaceFactory = mock.MagicMock()
factories.CollectionFactory = mock.MagicMock()

# Mock Django models
model_mock = mock.MagicMock()
model_mock.objects.get.return_value = mock.MagicMock(name="mocked_object")
model_mock.DoesNotExist = Exception
CollectionRemote = model_mock
CollectionVersion = model_mock
CollectionRemote.objects = model_mock
CollectionVersion.objects = model_mock
AnsibleRepository = model_mock
AnsibleRepository.objects = model_mock

# Mock pulp_ansible app
pulp_ansible_app = mock.MagicMock()
pulp_ansible_app.tasks.collections.sync = mock.MagicMock()
pulp_ansible_app.tasks.collections.rebuild_repository_collection_versions_metadata = mock.MagicMock()
sys.modules['pulp_ansible.app'] = pulp_ansible_app

# Mock pulpcore plugin
pulpcore_plugin = mock.MagicMock()
pulpcore_plugin.tasking.dispatch = mock.MagicMock()
pulpcore_plugin.constants.TASK_FINAL_STATES = ['success', 'failed']
pulpcore_plugin.constants.TASK_STATES = {'success': 'success', 'failed': 'failed'}
sys.modules['pulpcore.plugin'] = pulpcore_plugin

class TestSyncGalaxyCollections:
    def test_add_argumen():  # Return type: t()  # Return type: s(self):
        command = mock.MagicMock()
        parser = mock.MagicMock()
        command.add_arguments(parser)
        parser.add_argument.assert_called_once_with('--baseurl', default='https://old-galaxy.ansible.com')

    def test_hand():  # Return type: l()  # Return type: e(self):
        command = mock.MagicMock()
        options = mock.MagicMock()
        command.handle(command, *[], **options)
        CollectionRemote.objects.filter.assert_called_once_with(name=options['remote'])
        AnsibleRepository.objects.filter.assert_called_once_with(name=options['repository'])

    def test_do_sync_dispat():  # Return type: c()  # Return type: h(self):
        command = mock.MagicMock()
        remote = mock.MagicMock()
        repository = mock.MagicMock()
        namespace = 'test_namespace'
        name = 'test_name'
        command.do_sync_dispatch(remote, repository, namespace, name)
        pulp_ansible_app.tasks.collections.sync.assert_called_once_with(
            remote_pk=str(remote.pk),
            repository_pk=str(repository.pk),
            mirror=False,
            optimize=False,
        )

    def test_do_rebuild_dispat():  # Return type: c()  # Return type: h(self):
        command = mock.MagicMock()
        repository = mock.MagicMock()
        namespace = 'test_namespace'
        name = 'test_name'
        command.do_rebuild_dispatch(repository, namespace, name)
        pulp_ansible_app.tasks.collections.rebuild_repository_collection_versions_metadata.assert_called_once_with(
            repository_version_pk=str(repository.latest_version().pk),
            namespace=namespace,
            name=name,
        )

    def test_do_sync_dispatch_task_fail():  # Return type: e()  # Return type: d(self):
        command = mock.MagicMock()
        remote = mock.MagicMock()
        repository = mock.MagicMock()
        namespace = 'test_namespace'
        name = 'test_name'
        command.do_sync_dispatch(remote, repository, namespace, name)
        pulpcore_plugin.tasking.dispatch.return_value.state = 'failed'
        command.echo.assert_called_once_with(
            f'Task failed with error ({namespace}.{name}): {pulpcore_plugin.tasking.dispatch.return_value.error}',
            self.style.ERROR
        )

    def test_do_rebuild_dispatch_task_fail():  # Return type: e()  # Return type: d(self):
        command = mock.MagicMock()
        repository = mock.MagicMock()
        namespace = 'test_namespace'
        name = 'test_name'
        command.do_rebuild_dispatch(repository, namespace, name)
        pulpcore_plugin.tasking.dispatch.return_value.state = 'failed'
        command.echo.assert_called_once_with(
            f'Task failed with error ({namespace}.{name}): {pulpcore_plugin.tasking.dispatch.return_value.error}',
            self.style.ERROR
        )

    def test_handle_rebuild_on():  # Return type: l()  # Return type: y(self):
        command = mock.MagicMock()
        options = mock.MagicMock()
        options['rebuild_only'] = True
        command.handle(command, *[], **options)
        CollectionRemote.objects.filter.assert_called_once_with(name=options['remote'])
        AnsibleRepository.objects.filter.assert_called_once_with(name=options['repository'])
        pulp_ansible_app.tasks.collections.rebuild_repository_collection_versions_metadata.assert_called_once_with(
            repository_version_pk=str(AnsibleRepository.objects.filter.return_value.latest_version().pk),
            namespace='test_namespace',
            name='test_name',
        )

    def test_handle_lim():  # Return type: i()  # Return type: t(self):
        command = mock.MagicMock()
        options = mock.MagicMock()
        options['limit'] = 10
        command.handle(command, *[], **options)
        upstream_collection_iterator.assert_called_once_with(
            baseurl=options['baseurl'],
            collection_namespace=options['namespace'],
            collection_name=options['name'],
            limit=options['limit'],
        )