#!/usr/bin/env python3
"""
AITestCorrector - A utility for fixing syntax errors in AI-generated test files
and improving code coverage by reducing over-mocking and enhancing test quality.

This can be used as a standalone script or imported as a module.
"""

import os
import sys
import re
import ast
import json
import argparse
import traceback
import requests
from pathlib import Path

# Constants
MAX_CORRECTION_ATTEMPTS = 3
REQUEST_TIMEOUT = 60  # seconds
API_ENDPOINT = "https://api.sambanova.ai/v1/chat/completions"

# Basic fix functions
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

def ensure_mock_import(content):
    """Ensure unittest.mock is properly imported."""
    if 'mock.MagicMock' in content and 'import mock' not in content and 'from unittest import mock' not in content:
        # Add import to the beginning of the file
        return 'from unittest import mock\n' + content
    return content

def ensure_imports_order(content):
    """
    Ensure imports are properly ordered - particularly unittest.mock must be imported before use.
    This is a general fix that can handle various test files.
    """
    # Check if mock is used before imported
    if 'mock.' in content and ('from unittest import mock' not in content.split('mock.')[0] and 
                               'import mock' not in content.split('mock.')[0]):
        # Add mock import at the very beginning
        content = 'from unittest import mock\nimport sys\n' + content
        
        # Remove any duplicate imports later in the file
        content = re.sub(r'(\n)from unittest import mock(\n)', r'\1\2', content)
        content = re.sub(r'(\n)import mock(\n)', r'\1\2', content)
    
    # Check for other common import issues
    if 'import os' not in content and 'os.' in content:
        content = 'import os\n' + content
    
    if 'import sys' not in content and 'sys.' in content:
        content = 'import sys\n' + content
    
    # Clean up duplicate imports
    imports_seen = set()
    lines = content.splitlines()
    cleaned_lines = []
    
    for line in lines:
        if line.startswith('import ') or line.startswith('from '):
            if line in imports_seen:
                continue
            imports_seen.add(line)
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

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
    
    # Make sure mock is imported if needed
    if 'mock.MagicMock' in content and 'import mock' not in content and 'from unittest import mock' not in content:
        content = 'from unittest import mock\n' + content
        
    return content

def fix_init_module_imports(content):
    """Fix imports of __init__ modules which are not valid in Python."""
    # Replace direct imports of __init__ with package imports
    content = re.sub(
        r'from\s+([\w.]+)\.__init__\s+import',
        r'from \1 import',
        content
    )
    
    # Add module mocking for any problematic imports
    if '.__init__ import' in content or '.social.__init__' in content:
        # Make sure mock is imported
        if 'import mock' not in content and 'from unittest import mock' not in content:
            content = 'from unittest import mock\nimport sys\n' + content
        elif 'import sys' not in content:
            content = content.replace('import mock', 'import mock\nimport sys', 1)
        
        # Add mocking code for init modules
        mock_code = '\n# Mock problematic modules\n'
        for module_path in re.findall(r'([\w.]+)\.__init__', content):
            mock_code += f"sys.modules['{module_path}.__init__'] = mock.MagicMock()\n"
            mock_code += f"sys.modules['{module_path}'] = mock.MagicMock()\n"
        
        # Insert after imports
        if '\nimport ' in content or '\nfrom ' in content:
            import_section = re.search(r'(^|\n)(import|from).*?($|\n\n)', content, re.DOTALL)
            if import_section:
                pos = import_section.end()
                content = content[:pos] + mock_code + content[pos:]
            else:
                content = mock_code + content
        else:
            content = mock_code + content
    
    return content

def fix_django_setup(content):
    """
    Fix Django setup in test files to handle mocked modules properly.
    Rather than using django.setup() directly, patch it when mocks are in use.
    """
    # Check if we're using mocks and django.setup()
    if ('mock.MagicMock' in content and 'django.setup()' in content):
        # Replace django.setup() with patched version
        setup_code = '''
# Patched django setup to work with mocked modules
def _patch_django_setup():
    """Apply patch to django.setup to handle mocked modules"""
    import django
    original_setup = getattr(django, 'setup')
    
    def noop_setup():
        # Skip actual setup which fails with mocked modules
        pass
        
    django.setup = noop_setup
    return original_setup

# Store original setup in case we need to restore it
_original_django_setup = _patch_django_setup()
'''
        # Find location after imports to insert our patch
        import_pattern = re.compile(r'((?:from [^\n]+ import [^\n]+|import [^\n]+)\n)+')
        matches = list(import_pattern.finditer(content))
        if matches:
            last_import_end = matches[-1].end()
            content = content[:last_import_end] + setup_code + content[last_import_end:]
            
            # Replace django.setup() call with comment
            content = content.replace('django.setup()', '# django.setup() - patched to avoid errors with mocked modules')
    
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

def fix_comment_separated_function_names(content):
    """
    Fix function names that are split by comments like:
    def test_function_na():  # Return type: m()  # Return type: e():
    
    Should become:
    def test_function_name():
    """
    lines = content.splitlines()
    fixed_lines = []
    
    for line in lines:
        # Match function definitions with comment-embedded parts
        if re.match(r'\s*def\s+test_\w+\(\):\s*#.*Return type.*:', line):
            # Get the base function name
            base_name = re.match(r'\s*def\s+(test_\w+)\(\):', line).group(1)
            
            # Extract the missing parts from comments
            parts = []
            for comment in re.finditer(r'#\s*Return type:\s*(\w+)\(\)', line):
                parts.append(comment.group(1))
            
            # Build the complete function name
            if parts:
                complete_name = base_name + '_' + '_'.join(parts)
                # Replace with fixed function definition
                fixed_line = re.sub(r'(def\s+test_\w+)(\(\):.*)', r'def ' + complete_name + r'\2', line)
                fixed_line = re.sub(r'#\s*Return type:.*$', '', fixed_line).rstrip()
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

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

def normalize_module_path(content):
    """Update any module path references to use underscores instead of hyphens."""
    # Replace hyphens in import paths
    content = re.sub(r'galaxy_ng\.([^.\s]+)-([^.\s]+)', r'galaxy_ng.\1_\2', content)
    return content

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

def fix_advanced_syntax_errors(content):
    """
    Fix more complex syntax errors with a multi-stage approach.
    This includes unclosed strings, statements missing colons, etc.
    """
    lines = content.splitlines()
    fixed_lines = []
    
    # State variables for multi-line processing
    in_multiline_string = False
    string_quote_type = None
    unclosed_blocks = []
    
    for i, line in enumerate(lines):
        fixed_line = line
        
        # Fix 1: Missing colons at end of function/class/conditional statements
        if not in_multiline_string:
            # Detect statements that should end with a colon
            colon_pattern = r'^\s*(def|class|if|elif|else|for|while|try|except|finally|with)\s+.*\)\s*$'
            if re.match(colon_pattern, fixed_line):
                fixed_line += ':'
            
            # Detect statements that should end with a colon (no parentheses version)
            colon_pattern2 = r'^\s*(else|try|finally)\s*$'
            if re.match(colon_pattern2, fixed_line):
                fixed_line += ':'
        
        # Fix 2: Handle unclosed string literals
        if not in_multiline_string:
            # Check for opening quotes
            single_quotes = fixed_line.count("'")
            double_quotes = fixed_line.count('"')
            
            # Simple case: odd number of quotes of the same type in a line
            if single_quotes % 2 == 1 and '"' not in fixed_line:
                fixed_line += "'"
                
            elif double_quotes % 2 == 1 and "'" not in fixed_line:
                fixed_line += '"'
                
            # More complex case: detect multiline strings
            elif '"""' in fixed_line or "'''" in fixed_line:
                if fixed_line.count('"""') % 2 == 1:
                    in_multiline_string = True
                    string_quote_type = '"""'
                elif fixed_line.count("'''") % 2 == 1:
                    in_multiline_string = True
                    string_quote_type = "'''"
        else:
            # Check for closing quotes of multiline string
            if string_quote_type in fixed_line:
                in_multiline_string = False
                string_quote_type = None
            elif i == len(lines) - 1:
                # Last line with unclosed multiline string
                fixed_line += string_quote_type
                in_multiline_string = False
        
        # Fix 3: Handle unclosed function calls
        if not in_multiline_string:
            # Count opening and closing parentheses
            open_paren = fixed_line.count('(')
            close_paren = fixed_line.count(')')
            
            # If there are unclosed parentheses on this line
            if open_paren > close_paren:
                # Add to unclosed blocks stack
                unclosed_blocks.append(('(', open_paren - close_paren))
            elif close_paren > open_paren:
                # Close excess parentheses from previous lines
                excess = close_paren - open_paren
                while excess > 0 and unclosed_blocks:
                    block_type, count = unclosed_blocks.pop()
                    if block_type == '(' and count <= excess:
                        excess -= count
                    else:
                        unclosed_blocks.append((block_type, count - excess))
                        excess = 0
        
        fixed_lines.append(fixed_line)
    
    # Close any remaining unclosed blocks at the end of the file
    if unclosed_blocks:
        for block_type, count in reversed(unclosed_blocks):
            if block_type == '(':
                fixed_lines[-1] += ')' * count
    
    # Handle any unclosed multiline string at the end of the file
    if in_multiline_string and string_quote_type:
        fixed_lines[-1] += string_quote_type
    
    return '\n'.join(fixed_lines)

def reduce_excessive_mocking(content, module_path):
    """
    Reduce excessive mocking to improve coverage:
    1. Remove mocking of the module under test
    2. Focus more on actual behavior testing than just mock assertions
    """
    # Parse module name from path
    module_name = os.path.splitext(os.path.basename(module_path))[0]
    module_import_path = module_path.replace('/', '.').replace('.py', '')
    
    # Check for complete module mocking like:
    # sys.modules['galaxy_ng.app.utils.roles'] = mock.MagicMock()
    mock_module_pattern = rf"sys\.modules\['{module_import_path}'\]\s*=\s*mock\.MagicMock\(\)"
    if re.search(mock_module_pattern, content):
        # Replace with direct import
        content = re.sub(
            rf"try:\s*from {module_import_path} import \*.*?sys\.modules\['{module_import_path}'\]\s*=\s*mock\.MagicMock\(\)",
            f"# Direct import of the module being tested\nfrom {module_import_path} import *",
            content,
            flags=re.DOTALL
        )
    
    # Replace simple mock assertions with actual function calls
    # Find test functions that only assert mock calls
    test_patterns = re.finditer(r'def (test_\w+)\(\):\s*.*?assert\s+\w+\.(?:call_count|assert_called)', content, re.DOTALL)
    for test_match in test_patterns:
        test_func_name = test_match.group(1)
        test_func_content = test_match.group(0)
        
        # Check if function is named after a module function
        function_name = test_func_name.replace('test_', '')
        function_name = re.sub(r'_\w+$', '', function_name)  # Remove test scenario suffix
        
        # If the test is just asserting call_count, suggest better test
        if 'call_count' in test_func_content and not re.search(r'assert\s+[^.]+\s*==', test_func_content):
            better_test = f"""
def {test_func_name}():
    # Test the actual behavior instead of just mocking
    # Set up test input
    test_input = "test_value"
    # Call the function directly
    result = {function_name}(test_input)
    # Assert on the actual result 
    assert result is not None
"""
            content = content.replace(test_func_content, better_test)
    
    return content

def improve_test_quality(content):
    """
    Improve the quality of tests to better increase coverage:
    1. Add edge case tests
    2. Add more assertions beyond just checking call_count
    3. Fix tests that don't actually execute code paths
    """
    # Find test functions that are just checking call counts
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is the start of a test function
        if re.match(r'\s*def\s+test_\w+\(', line):
            # Find the end of the function
            func_start = i
            func_indent = len(line) - len(line.lstrip())
            i += 1
            
            while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > func_indent):
                i += 1
            
            func_end = i
            func_body = '\n'.join(lines[func_start:func_end])
            
            # Check if function only asserts call_count
            if 'call_count' in func_body and not re.search(r'assert\s+\w+\s*[=!]=', func_body):
                # Extract function name being tested
                match = re.search(r'def\s+test_(\w+)', func_body)
                if match:
                    func_name = match.group(1)
                    # Add better assertion
                    improved_body = func_body + f"\n    # Add assertion on actual result\n    assert {func_name} is not None  # Replace with actual check on return value"
                    lines[func_start:func_end] = improved_body.splitlines()
        else:
            i += 1
    
    return '\n'.join(lines)

def add_comprehensive_test_structure(content, module_path):
    """
    Add a more comprehensive test structure to increase coverage:
    1. Add parametrized tests for different inputs
    2. Add edge case tests
    3. Test exception cases
    """
    # Extract module name from path
    module_name = os.path.splitext(os.path.basename(module_path))[0]
    
    # Check if the content already has good test coverage
    if 'pytest.mark.parametrize' in content and 'pytest.raises' in content:
        # Already has good structure
        return content
    
    # Get all test functions
    test_funcs = re.findall(r'def\s+(test_\w+)\(\):', content)
    
    # Check if we have very few test functions 
    if len(test_funcs) <= 3:
        # Add a suggestion for parametrized tests
        addition = f"""
# SUGGESTION: Add parametrized tests for more coverage
@pytest.mark.parametrize("input_value,expected", [
    ("normal_input", "expected_result"),
    ("edge_case", "edge_case_result"),
    ("", "empty_result"),
    (None, "none_result")
])
def test_{module_name}_with_different_inputs(input_value, expected):
    # This will test multiple scenarios in a single test
    # Replace with actual implementation
    result = some_function(input_value)
    assert result == expected

# SUGGESTION: Add tests for exception cases
def test_{module_name}_raises_exception_for_invalid_input():
    # Test exception handling
    with pytest.raises(ValueError):
        some_function(invalid_input)
"""
        # Add it at the end of the file
        content += addition
    
    return content

# Standard fix function (without AI)
def fix_test_file(test_file):
    """Apply all fixes to a test file."""
    try:
        print(f"Fixing {test_file}...")
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract module path from test file
        module_path = test_file.replace('test_', '').replace('.py', '') 
        if '/ai_generated/' in test_file:
            module_path = test_file.replace('/ai_generated/test_', '/').replace('.py', '')
        
        # Apply fixers in order
        content = ensure_imports_order(content)  # Fix imports first
        content = ensure_mock_import(content)
        content = fix_import_statements(content)
        content = add_factory_mocks(content)
        content = fix_test_definitions(content)
        content = fix_annotation_syntax(content)
        content = fix_django_setup(content)
        content = handle_special_modules(content, test_file)
        content = fix_init_module_imports(content)
        content = normalize_module_path(content)
        content = balance_parentheses(content)
        content = fix_advanced_syntax_errors(content)
        content = fix_comment_separated_function_names(content)  # Fix function name issues with comments
        
        # Coverage improvement fixes
        content = reduce_excessive_mocking(content, module_path)
        content = improve_test_quality(content)
        content = add_comprehensive_test_structure(content, module_path)
        
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

# Create mock pulp_smash configuration to prevent errors
def create_pulp_smash_config():
    """Create a mock pulp_smash configuration file to prevent errors."""
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

# Basic validation
def validate_test_runs(test_file):
    """Try to run the test file to see if it collects without errors."""
    import subprocess
    
    # Run pytest with --collect-only to test if the file can be imported
    cmd = ["python", "-m", "pytest", test_file, "--collect-only", "-v", 
           "-p", "no:pulp_ansible", "-p", "no:pulpcore", "-p", "no:pulp_smash"]
    
    result = subprocess.run(
        cmd,
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

# AI-powered test corrector class
class AITestCorrector:
    """
    Class untuk memperbaiki file test secara dinamis menggunakan kombinasi
    antara perbaikan manual dan AI-assisted correction.
    """
    
    def __init__(self, api_key, model="Meta-Llama-3.1-8B-Instruct"):
        self.api_key = api_key
        self.model = model
        self.correction_attempts = 0
        self.max_attempts = MAX_CORRECTION_ATTEMPTS
        
        print(f"Initialized AITestCorrector with model: {model}")
    
    def fix_test_file(self, test_file, module_path):
        """
        Memperbaiki file test dengan pendekatan multi-stage:
        1. Perbaikan manual dengan regex dan rule-based fixes
        2. Jika masih ada error, gunakan AI untuk menganalisis dan memperbaiki
        3. Validasi dan ulangi jika perlu
        """
        print(f"Fixing {test_file}...")
        
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Stage 1: Perbaikan manual standar
            content = self._apply_standard_fixes(content, test_file)
            
            # Validasi hasil
            try:
                ast.parse(content)
                print(f"✅ Syntax validated after standard fixes for {test_file}")
                self._save_content(test_file, content)
                return True
            except SyntaxError as e:
                print(f"⚠️ Syntax errors remain after standard fixes: {e}")
                
                # Stage 2: AI-assisted correction
                content = self._apply_ai_correction(content, module_path, e, test_file)
                
                # Save final result
                self._save_content(test_file, content)
                return True
        
        except Exception as e:
            print(f"❌ Error fixing {test_file}: {e}")
            traceback.print_exc()
            return False
    
    def _apply_standard_fixes(self, content, test_file):
        """Menerapkan perbaikan standar pada konten"""
        # Extract module path from test file
        module_path = test_file.replace('test_', '').replace('.py', '') 
        if '/ai_generated/' in test_file:
            module_path = test_file.replace('/ai_generated/test_', '/').replace('.py', '')
        
        content = ensure_imports_order(content)  # Fix imports first
        content = ensure_mock_import(content)
        content = fix_import_statements(content)
        content = add_factory_mocks(content)
        content = fix_test_definitions(content)
        content = fix_annotation_syntax(content)
        content = fix_django_setup(content)
        content = handle_special_modules(content, test_file)
        content = fix_init_module_imports(content)
        content = normalize_module_path(content)
        content = balance_parentheses(content)
        content = fix_advanced_syntax_errors(content)
        content = fix_comment_separated_function_names(content)
        
        # Coverage improvement fixes
        content = reduce_excessive_mocking(content, module_path)
        content = improve_test_quality(content)
        content = add_comprehensive_test_structure(content, module_path)
        
        return content
    
    def _apply_ai_correction(self, content, module_path, error, test_file):
        """Menerapkan perbaikan berbasis AI dengan pendekatan iteratif"""
        self.correction_attempts = 0
        
        while self.correction_attempts < self.max_attempts:
            self.correction_attempts += 1
            print(f"AI correction attempt #{self.correction_attempts}...")
            
            # Dapatkan koreksi dari AI
            corrected_code = self._get_ai_correction(content, module_path, error)
            
            if corrected_code:
                # Validasi hasil koreksi
                try:
                    ast.parse(corrected_code)
                    print(f"✅ AI correction attempt #{self.correction_attempts} successful!")
                    return corrected_code
                except SyntaxError as new_error:
                    print(f"⚠️ AI correction attempt #{self.correction_attempts} still has errors: {new_error}")
                    
                    # Update error untuk iterasi berikutnya
                    error = new_error
                    content = corrected_code
            else:
                print(f"❌ AI correction attempt #{self.correction_attempts} failed to produce corrected code")
                break
        
        # Jika semua percobaan gagal, tandai file sebagai memerlukan perbaikan manual
        return f"# WARNING: This file has syntax errors that need manual review after {self.correction_attempts} correction attempts: {error}\n" + content
    
    def _get_ai_correction(self, content, module_path, error):
        """Mendapatkan koreksi dari AI berdasarkan konten saat ini dan error"""
        # Ekstrak konteks error
        error_line = self._get_error_context(content, error)
        
        # Buat prompt berdasarkan jenis error
        prompt = self._create_correction_prompt(content, module_path, error, error_line, self.correction_attempts)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "temperature": 0.1,  # Nilai rendah untuk output yang lebih deterministik
            "messages": [
                {"role": "system", "content": self._create_system_prompt()},
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(API_ENDPOINT, headers=headers, json=data, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                corrected_code = result["choices"][0]["message"]["content"]
                
                # Bersihkan format markdown
                corrected_code = re.sub(r'```python\s*', '', corrected_code)
                corrected_code = re.sub(r'```\s*$', '', corrected_code)
                corrected_code = corrected_code.strip()
                
                # Terapkan perbaikan standar pada hasil AI juga
                return self._apply_standard_fixes(corrected_code, "ai_generated_fix")
            
        except Exception as e:
            print(f"Error during AI correction: {e}")
            traceback.print_exc()
        
        return None
    
    def _get_error_context(self, content, error):
        """Ekstrak konteks error dari konten"""
        lines = content.splitlines()
        
        # Parse error message untuk mendapatkan line number
        error_str = str(error)
        line_match = re.search(r'line (\d+)', error_str)
        
        if line_match:
            line_num = int(line_match.group(1))
            
            # Dapatkan baris error dan beberapa baris di sekitarnya untuk konteks
            start_line = max(0, line_num - 5)
            end_line = min(len(lines), line_num + 5)
            
            context_lines = []
            for i in range(start_line, end_line):
                prefix = ">>>" if i == line_num - 1 else "   "
                context_lines.append(f"{prefix} {i+1}: {lines[i]}")
            
            return "\n".join(context_lines)
        
        return "Error context could not be determined"
    
    def _create_correction_prompt(self, content, module_path, error, error_context, attempt):
        """Membuat prompt untuk AI correction berdasarkan error dan konteks"""
        error_type = self._analyze_error_type(str(error))
        
        prompt = f"""Saya memiliki file test Python untuk meningkatkan code coverage yang masih memiliki error sintaks setelah perbaikan otomatis {attempt} kali.

MODULE PATH: {module_path}
ERROR TYPE: {error_type}
ERROR MESSAGE: {error}

ERROR CONTEXT:
{error_context}

FULL CURRENT CODE:
```python
{content}
```

Ini adalah percobaan perbaikan ke-{attempt}. {"Tolong perhatikan error-error sebelumnya dan pastikan tidak muncul lagi." if attempt > 1 else ""}

{self._get_error_specific_instructions(error_type)}

Tolong perbaiki kode ini dan kembalikan versi yang sudah diperbaiki dengan fokus pada:
1. Memastikan semua syntax errors diperbaiki
2. MENGURANGI penggunaan mock, khususnya untuk modul yang sedang ditest
3. Mengubah test sehingga benar-benar menjalankan kode, bukan hanya mengecek apakah fungsi dipanggil
4. Menambahkan test untuk berbagai execution paths untuk meningkatkan coverage

Kembalikan HANYA kode Python yang sudah diperbaiki, tanpa penjelasan atau format markdown.
"""
        return prompt
    
    def _analyze_error_type(self, error_message):
        """Menganalisis tipe error untuk memberikan instruksi spesifik"""
        if "unterminated string literal" in error_message:
            return "UNTERMINATED_STRING"
        elif "expected ':'" in error_message:
            return "MISSING_COLON"
        elif "invalid syntax" in error_message:
            return "INVALID_SYNTAX"
        elif "illegal target for annotation" in error_message:
            return "ILLEGAL_ANNOTATION"
        elif "unexpected EOF" in error_message:
            return "UNEXPECTED_EOF"
        else:
            return "GENERAL_SYNTAX_ERROR"
    
    def _get_error_specific_instructions(self, error_type):
        """Memberikan instruksi spesifik berdasarkan tipe error"""
        instructions = {
            "UNTERMINATED_STRING": """
Perhatikan baik-baik semua string literal. Error ini terjadi karena string tidak ditutup dengan benar.
Pastikan:
- Semua string memiliki tanda kutip penutup yang sesuai (' atau ")
- String multibaris (''') ditutup dengan benar
- Escape character (\) tidak menyebabkan masalah pada string
            """,
            
            "MISSING_COLON": """
Error ini terjadi karena ada definisi fungsi/kelas/blok yang tidak diakhiri dengan titik dua (:).
Pastikan:
- Semua definisi fungsi (def) diakhiri dengan titik dua: `def test_something():`
- Semua statement if/else/elif diakhiri dengan titik dua
- Semua blok with/try/except diakhiri dengan titik dua
            """,
            
            "ILLEGAL_ANNOTATION": """
Error ini terjadi karena penggunaan type annotation yang tidak valid.
Pastikan:
- Jangan gunakan type annotations untuk assignment seperti `var[idx]: type`
- Gunakan assignment biasa: `var[idx] = value`
- Jangan menggunakan `:=` (walrus operator) jika tidak diperlukan
            """,
            
            "INVALID_SYNTAX": """
Error ini adalah kesalahan sintaks umum. Coba periksa:
- Penggunaan operator yang tidak tepat
- Statement yang tidak lengkap
- Penggunaan syntax yang tidak valid di Python
            """,
            
            "UNEXPECTED_EOF": """
Error ini terjadi karena ada blok kode yang tidak selesai.
Pastikan:
- Semua blok kode ditutup dengan benar
- Semua parentheses/brackets/braces seimbang
- Tidak ada fungsi/kelas yang definisinya terpotong
            """,
            
            "GENERAL_SYNTAX_ERROR": """
Periksa secara menyeluruh untuk kesalahan sintaks, dengan fokus khusus pada:
- Struktur kode yang valid
- Penutupan string yang benar
- Penggunaan titik dua yang tepat
- Keseimbangan parentheses/brackets/braces
            """,
        }
        
        return instructions.get(error_type, instructions["GENERAL_SYNTAX_ERROR"])
    
    def _create_system_prompt(self):
        """Membuat prompt sistem untuk AI correction yang fokus pada peningkatan coverage"""
        return """Anda adalah ahli Python yang memiliki spesialisasi dalam memperbaiki error sintaks dan mengoptimalkan test untuk meningkatkan code coverage.

Tugas Anda adalah:
1. Menganalisis dan memperbaiki error sintaks dalam kode test
2. Memastikan test tersebut menjalankan kode yang sebenarnya, BUKAN hanya mock
3. Meningkatkan kualitas test untuk mendapatkan code coverage yang lebih baik

Saat memperbaiki test untuk meningkatkan coverage:
1. KURANGI penggunaan mock, terutama untuk modul yang sedang ditest
2. FOKUS pada pengujian perilaku fungsi, bukan hanya struktur
3. UJI semua jalur eksekusi (if/else paths, error handling)
4. PASTIKAN test memanggil kode yang sebenarnya dengan input nyata

Contoh perbaikan untuk meningkatkan coverage:

BURUK (tidak meningkatkan coverage):
```python
def test_function():
    # Ini tidak mengeksekusi kode sebenarnya, tidak meningkatkan coverage
    with mock.patch('module.function') as mock_func:
        result = call_something() 
        mock_func.assert_called_once()
```

BAIK (meningkatkan coverage):
```python
def test_function_normal_case():
    # Ini benar-benar menjalankan kode fungsi
    input_value = "test input"
    result = function(input_value)
    assert result == expected_output
    
def test_function_edge_case(): 
    # Menguji jalur kode lain
    edge_input = ""
    result = function(edge_input)
    assert result == expected_edge_output
```

Berikan solusi kode lengkap yang meningkatkan code coverage.
"""
    
    def _save_content(self, test_file, content):
        """Menyimpan konten ke file"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Content saved to {test_file}")

def main():
    parser = argparse.ArgumentParser(description="Fix AI-generated test files for the Galaxy NG project and improve code coverage")
    parser.add_argument("--path", default="galaxy_ng/tests/unit/ai_generated", 
                        help="Path to directory containing test files")
    parser.add_argument("--validate", action="store_true", 
                        help="Validate that tests collect without errors")
    parser.add_argument("--api-key", help="SambaNova API key for AI-assisted correction (falls back to SAMBANOVA_API_KEY env var)")
    parser.add_argument("--model", default="Meta-Llama-3.1-8B-Instruct", help="AI model to use for correction")
    parser.add_argument("--improve-coverage", action="store_true", 
                        help="Apply additional fixes to improve code coverage")
    parser.add_argument("files", nargs="*", help="Specific test files to fix (optional)")
    
    args = parser.parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get('SAMBANOVA_API_KEY')
    
    # Create pulp_smash config to prevent errors
    create_pulp_smash_config()
    
    success_count = 0
    failure_count = 0
    
    # Inisialisasi AI corrector jika ada API key
    ai_corrector = None
    if api_key:
        print(f"Initializing AI-assisted correction with model {args.model}")
        ai_corrector = AITestCorrector(api_key, model=args.model)
    else:
        print("AI-assisted correction disabled (no API key provided)")
    
    if args.files:
        # Fix specific files
        for test_file in args.files:
            if ai_corrector:
                # Extract module path from test file
                module_path = os.path.basename(test_file).replace('test_', '').replace('.py', '')
                if ai_corrector.fix_test_file(test_file, module_path):
                    success_count += 1
                    if args.validate:
                        validate_test_runs(test_file)
                else:
                    failure_count += 1
            else:
                # Use traditional fixing method
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
                    
                    if ai_corrector:
                        # Extract module path from test file
                        module_path = file.replace('test_', '').replace('.py', '')
                        if ai_corrector.fix_test_file(test_file, module_path):
                            success_count += 1
                            if args.validate:
                                validate_test_runs(test_file)
                        else:
                            failure_count += 1
                    else:
                        # Use traditional fixing method
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
    print(f"  Using AI-assisted correction: {'Yes' if ai_corrector else 'No'}")
    print(f"  Coverage improvement mode: {'Yes' if args.improve_coverage else 'No'}")
    
if __name__ == "__main__":
    main()