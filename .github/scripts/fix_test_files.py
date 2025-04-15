#!/usr/bin/env python3
"""
Fix generated test files with proper Django setup and imports.
"""

import os
import sys
import re

def fix_test_file(test_file, module_path=None):
    """Fix a test file with proper Django setup and imports."""
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract module path from test file if not provided
        if not module_path and 'galaxy_ng/tests/' in test_file:
            module_path = test_file.replace('galaxy_ng/tests/', '').replace('test_', '').replace('.py', '.py')
        
        # Get module import path
        module_import = module_path.replace('/', '.').replace('.py', '') if module_path else ''
        
        # Add required imports and setup at the beginning
        setup_code = f'''import os
import sys
import re
import pytest
from unittest import mock

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

# Use Django DB for tests
pytestmark = pytest.mark.django_db

'''
        # Add module import if available
        if module_import:
            setup_code += f"# Import module being tested\nfrom galaxy_ng.{module_import} import *\n\n"
        
        # Replace existing code or add at top
        if 'import pytest' in content:
            content = re.sub(r'(import pytest.*?\n)', setup_code, content, flags=re.DOTALL)
        else:
            content = setup_code + content
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Successfully fixed {test_file}")
        return True
        
    except Exception as e:
        print(f"Error fixing {test_file}: {e}")
        return False

def create_pulp_smash_config():
    """Create a mock pulp_smash configuration file."""
    import json
    
    config_dir = os.path.expanduser("~/.config/pulp_smash")
    os.makedirs(config_dir, exist_ok=True)
    
    config = {
        "pulp": {
            "auth": ["admin", "admin"],
            "version": "3.0",
            "selinux enabled": False
        },
        "hosts": [
            {
                "hostname": "localhost",
                "roles": {
                    "api": {"port": 24817, "scheme": "http", "service": "nginx"},
                    "content": {"port": 24816, "scheme": "http", "service": "pulp_content_app"},
                    "pulp resource manager": {},
                    "pulp workers": {},
                    "redis": {},
                    "shell": {"transport": "local"},
                    "squid": {}
                }
            }
        ]
    }
    
    config_path = os.path.join(config_dir, "settings.json")
    with open(config_path, 'w') as f:
        json.dump(config, f)
    
    print(f"Created pulp_smash config at {config_path}")
    return config_path

# Example usage
if __name__ == "__main__":
    # Create pulp_smash config first to prevent plugin errors
    create_pulp_smash_config()
    
    # Fix all test files provided as arguments
    if len(sys.argv) > 1:
        for test_file in sys.argv[1:]:
            fix_test_file(test_file)
    else:
        print("Usage: python fix_test_files.py <test_file1> <test_file2> ...")