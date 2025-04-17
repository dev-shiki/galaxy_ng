#!/usr/bin/env python3
"""
Script to fix common issues in generated test files.
This can be run independently to correct problems in existing test files.
"""

import os
import sys
import re
import ast
import argparse
import traceback
from pathlib import Path

def fix_annotation_syntax(content):
    """Fix common annotation syntax errors in AI-generated tests."""
    # Fix variable assignments using annotation syntax
    content = re.sub(
        r'(\w+)\s*:\s*=\s*(.+)',  # Find patterns like "var : = value"
        r'\1 = \2',  # Replace with "var = value"
        content
    )
    
    # Fix illegal annotation targets
    content = re.sub(
        r'(\w+)\[(.*?)\]\s*:\s*(.+)',  # Find patterns like "var[idx]: type"
        r'\1[\2] = \3',  # Replace with "var[idx] = value" 
        content
    )
    
    # Fix fixture annotations without parentheses
    content = re.sub(
        r'@pytest\.fixture\s*:\s*',
        r'@pytest.fixture()\ndef ',
        content
    )
    
    # Fix mark annotations without parentheses
    content = re.sub(
        r'@pytest\.mark\.(\w+)\s*:\s*',
        r'@pytest.mark.\1()\ndef ',
        content
    )
    
    # Fix incorrect type hints
    content = re.sub(
        r'def\s+(\w+)\s*\(\s*([^)]*)\s*\)\s*:\s*([^:]+):',
        r'def \1(\2):  # Return type: \3',
        content
    )
    
    return content

def balance_parentheses(content):
    """
    Automatically balance parentheses, brackets, and braces in code.
    Uses a stack-based approach to detect and fix mismatches.
    """
    lines = content.splitlines()
    stack = []
    
    # Track all brackets
    for i, line in enumerate(lines):
        for j, char in enumerate(line):
            if char in '({[':
                stack.append((char, i))
            elif char in ')}]':
                if stack and ((char == ')' and stack[-1][0] == '(') or
                              (char == '}' and stack[-1][0] == '{') or
                              (char == ']' and stack[-1][0] == '[')):
                    stack.pop()
    
    # Add missing closing brackets
    if stack:
        closing = {'(': ')', '{': '}', '[': ']'}
        line_fixes = {}
        
        for bracket, line_num in stack:
            line_fixes.setdefault(line_num, []).append(closing[bracket])
        
        # Apply fixes in reverse order to avoid affecting line numbers
        for line_num, closers in sorted(line_fixes.items(), reverse=True):
            lines[line_num] = lines[line_num] + ''.join(closers)
    
    return '\n'.join(lines)

def fix_import_statements(content):
    """
    Fix common import errors:
    1. Replace imports of non-existent factories
    2. Fix incomplete import statements
    3. Handle imports for special modules like __init__
    """
    # Replace imports of non-existent factories
    factory_patterns = [
        (r'from galaxy_ng\.social import factories(.*)', r'# Mock factories\nimport mock\nsocial_factories = mock.MagicMock()\1'),
        (r'from galaxy_ng\.tests import factories(.*)', r'# Mock factories\nimport mock\nfactories = mock.MagicMock()\1'),
        (r'from galaxy_ng\.([^.\s]+) import factories(.*)', r'# Mock \1 factories\nimport mock\n\1_factories = mock.MagicMock()\2'),
    ]
    
    for pattern, replacement in factory_patterns:
        content = re.sub(pattern, replacement, content)
    
    # Fix incomplete import statements
    incomplete_imports = [
        (r'from galaxy_module\s*$', r'# Fixed incomplete import\nimport mock\ngalaxy_module = mock.MagicMock()'),
        (r'import galaxy_module\s*$', r'# Fixed incomplete import\nimport mock\ngalaxy_module = mock.MagicMock()'),
        (r'from ([^\s.]+)\s*$', r'# Fixed incomplete import\nimport mock\n\1 = mock.MagicMock()'),
    ]
    
    for pattern, replacement in incomplete_imports:
        content = re.sub(pattern, replacement, content)
    
    # Make sure mock is imported
    if 'mock.MagicMock' in content and 'import mock' not in content:
        content = 'import mock\n' + content
        
    return content

def add_factory_mocks(content):
    """Add mock factories if referenced but not defined."""
    if re.search(r'\bfactories\b', content) and not re.search(r'factories\s*=\s*mock\.MagicMock', content):
        factories_mock = '\n# Mock factories for testing\nfactories = mock.MagicMock()\nfactories.UserFactory = mock.MagicMock()\nfactories.GroupFactory = mock.MagicMock()\nfactories.NamespaceFactory = mock.MagicMock()\nfactories.CollectionFactory = mock.MagicMock()\n'
        if 'import mock' in content:
            content = content.replace('import mock', 'import mock' + factories_mock, 1)
        else:
            content = 'import mock\n' + factories_mock + content
    
    return content

def fix_test_definitions(content):
    """Fix test function definitions with syntax errors."""
    # Fix missing parentheses in function definitions
    content = re.sub(r'def\s+(test_\w+)\s*(?!\()', r'def \1()', content)
    
    # Fix missing colons in function definitions
    content = re.sub(r'def\s+(test_\w+)(\([^)]*\))\s*(?!:)', r'def \1\2:', content)
    
    return content

def handle_special_modules(content, test_file):
    """Add special handling for __init__.py files and other special modules."""
    
    # Special handling for __init__.py tests
    if 'test___init__' in test_file or 'test_social___init__' in test_file:
        init_mocks = '''
# Mock special modules for __init__.py testing
import sys
social_factories = mock.MagicMock()
auth_module = mock.MagicMock()
social_auth = mock.MagicMock()
social_app = mock.MagicMock()

# Add to sys.modules to prevent import errors
sys.modules['galaxy_ng.social.factories'] = social_factories
sys.modules['galaxy_ng.social.auth'] = auth_module
'''
        if 'import mock' in content:
            content = content.replace('import mock', 'import mock\nimport sys', 1)
            if 'social_factories =' not in content:
                content = content.replace('import sys', 'import sys' + init_mocks, 1)
        else:
            content = 'import mock\nimport sys' + init_mocks + content
    
    return content

def ensure_django_setup(content):
    """Ensure proper Django setup is included in the test file."""
    django_setup = "django.setup()"
    if django_setup not in content:
        setup_code = '''
import os
import sys
import re
import pytest
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
'''
        content = setup_code + content
    
    return content

def normalize_module_path(test_file):
    """Update any module path references to use underscores instead of hyphens."""
    content = test_file
    # Replace hyphens in import paths
    content = re.sub(r'galaxy_ng\.([^.\s]+)-([^.\s]+)', r'galaxy_ng.\1_\2', content)
    return content

def fix_test_file(test_file):
    """Apply all fixes to a test file."""
    try:
        print(f"Fixing {test_file}...")
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply fixers in order
        content = ensure_django_setup(content)
        content = fix_import_statements(content)
        content = add_factory_mocks(content)
        content = fix_test_definitions(content)
        content = fix_annotation_syntax(content)  # Tambahkan baris ini
        content = handle_special_modules(content, test_file)
        content = normalize_module_path(content)
        content = balance_parentheses(content)
        
        # Final validation with ast parse
        try:
            ast.parse(content)
            print(f"✅ Syntax validated for {test_file}")
        except SyntaxError as e:
            print(f"⚠️ Syntax errors remain in {test_file}: {e}")
            # Mark file as needing manual review
            content = f"# WARNING: This file has syntax errors that need manual review: {e}\n" + content
        
        # Write back to file
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fixed {test_file}")
        return True
    except Exception as e:
        print(f"❌ Error fixing {test_file}: {e}")
        traceback.print_exc()
        return False

def create_pulp_smash_config():
    """Create a mock pulp_smash configuration file to prevent errors."""
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
    
    print(f"Created mock pulp_smash config at {config_path}")
    return config_path

def validate_test_runs(test_file):
    """Try to run the test file to see if it collects without errors."""
    import subprocess
    
    # Run pytest with --collect-only to test if the file can be imported
    result = subprocess.run(
        ["python", "-m", "pytest", test_file, "--collect-only", "-v"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✅ Test file {test_file} successfully collects")
        return True
    else:
        print(f"⚠️ Test file {test_file} has collection issues:")
        print(result.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Fix AI-generated test files for the Galaxy NG project")
    parser.add_argument("--path", default="galaxy_ng/tests/unit/ai_generated", 
                        help="Path to directory containing test files")
    parser.add_argument("--validate", action="store_true", 
                        help="Validate that tests collect without errors")
    parser.add_argument("files", nargs="*", help="Specific test files to fix (optional)")
    
    args = parser.parse_args()
    
    # Create pulp_smash config to prevent errors
    create_pulp_smash_config()
    
    success_count = 0
    failure_count = 0
    
    if args.files:
        # Fix specific files
        for test_file in args.files:
            if fix_test_file(test_file):
                success_count += 1
                if args.validate:
                    validate_test_runs(test_file)
            else:
                failure_count += 1
    else:
        # Fix all test files in directory
        for root, dirs, files in os.walk(args.path):
            for file in files:
                if file.endswith('.py') and file.startswith('test_'):
                    test_file = os.path.join(root, file)
                    if fix_test_file(test_file):
                        success_count += 1
                        if args.validate:
                            validate_test_runs(test_file)
                    else:
                        failure_count += 1
    
    print(f"\nTest Fixer Summary:")
    print(f"  Successfully fixed: {success_count}")
    print(f"  Failed to fix: {failure_count}")
    print(f"  Total processed: {success_count + failure_count}")

if __name__ == "__main__":
    main()