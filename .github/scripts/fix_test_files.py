#!/usr/bin/env python3
"""
Script to fix common issues in generated test files.
"""

import os
import sys
import re
import ast
import argparse

def fix_test_file(test_file):
    """
    Fix common issues in a generated test file:
    - Module import paths with hyphens
    - Syntax errors in test functions
    - Missing mock factories
    - Improper Django setup
    """
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix imports (replace hyphens with underscores)
        fixed_content = re.sub(
            r'from galaxy_ng\.([^-\s]+)-([^-\s]+)', 
            r'from galaxy_ng.\1_\2', 
            content
        )
        fixed_content = re.sub(
            r'import galaxy_ng\.([^-\s]+)-([^-\s]+)', 
            r'import galaxy_ng.\1_\2', 
            fixed_content
        )
        
        # Replace other occurrences of hyphens in module paths
        hyphen_paths = re.findall(r'galaxy_ng\.[^-\s]+-[^-\s]+', fixed_content)
        for path in hyphen_paths:
            fixed_path = path.replace('-', '_')
            fixed_content = fixed_content.replace(path, fixed_path)
        
        # Mock factories if referenced but not defined
        if "factories" in fixed_content and "factories = mock.MagicMock()" not in fixed_content:
            factories_mock = '\n# Mock factories for testing\nfactories = mock.MagicMock()\nfactories.UserFactory = mock.MagicMock()\nfactories.GroupFactory = mock.MagicMock()\nfactories.NamespaceFactory = mock.MagicMock()\nfactories.CollectionFactory = mock.MagicMock()\n'
            if 'import mock' in fixed_content:
                fixed_content = fixed_content.replace('import mock', 'import mock' + factories_mock)
            else:
                fixed_content = 'import mock\n' + factories_mock + fixed_content
        
        # Check for proper Django setup
        django_setup = "django.setup()"
        if django_setup not in fixed_content:
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
            fixed_content = setup_code + fixed_content
        
        # Check for syntax errors
        try:
            ast.parse(fixed_content)
        except SyntaxError as e:
            line_no = e.lineno if hasattr(e, 'lineno') else 0
            print(f"Syntax error in {test_file} at line {line_no}: {e}")
            
            # Extract problematic lines and try to fix
            lines = fixed_content.splitlines()
            if 0 < line_no <= len(lines):
                problem_line = lines[line_no-1]
                # Check for test function definition issues
                if 'def test_' in problem_line and not problem_line.strip().endswith(':'):
                    if '(' not in problem_line:
                        lines[line_no-1] = problem_line + '():'
                    else:
                        lines[line_no-1] = problem_line + ':'
                    fixed_content = '\n'.join(lines)
                    print(f"Fixed syntax in function definition: {lines[line_no-1]}")
        
        # Write the fixed content back to the file
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print(f"Successfully fixed issues in {test_file}")
        return True
    
    except Exception as e:
        print(f"Error fixing {test_file}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Fix common issues in generated test files")
    parser.add_argument("files", nargs="+", help="Test files to fix")
    
    args = parser.parse_args()
    
    success_count = 0
    for test_file in args.files:
        if fix_test_file(test_file):
            success_count += 1
    
    print(f"Fixed {success_count}/{len(args.files)} test files")

if __name__ == "__main__":
    main()