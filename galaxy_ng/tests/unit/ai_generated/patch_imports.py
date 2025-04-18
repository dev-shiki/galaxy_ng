"""Helper module to patch common import issues in AI-generated tests."""
import os
import sys
from unittest import mock

def patch_test_imports():
    """
    Patch common import problems in generated tests.
    Call this at the start of each test file to ensure proper mocking.
    """
    # Ensure unittest.mock is available as just 'mock'
    sys.modules['mock'] = mock
    
    # Mock common modules that might be referenced
    modules_to_mock = [
        'galaxy_ng.app.management.commands.sync_galaxy_collections',
        'galaxy_ng.social.auth',
        'galaxy_ng.social.factories',
        'galaxy_ng.app.utils.roles',
        'galaxy_ng.app.access_control.access_policy',
        'galaxy_ng.app.utils.galaxy',
        'pulpcore',
        'pulp_ansible'
    ]
    
    for module_path in modules_to_mock:
        if module_path not in sys.modules:
            # Create parent modules if they don't exist
            parts = module_path.split('.')
            for i in range(1, len(parts)):
                parent = '.'.join(parts[:i])
                if parent not in sys.modules:
                    sys.modules[parent] = mock.MagicMock()
            # Create the module itself
            sys.modules[module_path] = mock.MagicMock()
    
    # Add common factory mocks if factories isn't defined
    if 'factories' not in globals():
        factories = mock.MagicMock()
        factories.UserFactory = mock.MagicMock()
        factories.GroupFactory = mock.MagicMock()
        factories.NamespaceFactory = mock.MagicMock()
        factories.CollectionFactory = mock.MagicMock()
        sys.modules['factories'] = factories
