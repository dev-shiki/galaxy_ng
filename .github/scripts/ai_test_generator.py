#!/usr/bin/env python3
"""
This script uses the SambaNova API to generate test code for modules
with low test coverage. Fixed to handle Galaxy NG path structure correctly.
"""

import os
import sys
import json
import time
import argparse
import requests
import re
import ast
import traceback
from pathlib import Path

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 60  # seconds

# Default system prompt for AI test generation
def update_system_prompt():
    """Create a comprehensive system prompt for AI test generation that produces tests with better coverage."""
    return """You are an expert Python developer specializing in writing highly effective pytest tests for Django applications.
Your task is to analyze the provided code and generate comprehensive pytest tests that maximize code coverage and follow these strict rules:

CRITICAL GUIDELINES FOR GENERATING HIGH-COVERAGE TESTS:

1. FOCUS ON REAL CODE EXECUTION:
   - DON'T mock the module under test - the goal is to execute the real code to increase coverage
   - Only mock external dependencies that would be problematic in a test environment
   - Use real objects when possible rather than mocks
   - Create tests that exercise different execution paths in the code

2. TEST BEHAVIOR, NOT STRUCTURE:
   - Focus on what the code DOES, not just that functions were called
   - Test the actual outputs and side effects of functions
   - Verify all return values with specific assertions
   - Include edge cases, boundary values, and error conditions

3. SMART USE OF MOCKING:
   - Only mock external services, APIs, or databases that cannot be easily used in tests
   - Avoid creating test files that import a module and immediately mock it completely
   - Use patch() as a context manager or decorator for specific external dependencies
   - Set meaningful return values for mocked methods that match real behavior

4. DJANGO ENVIRONMENT SETUP:
   - Include proper Django environment setup at the top of each test file
   - Use pytest fixtures to set up database state
   - Leverage pytest.mark.django_db for tests that need database access

5. ENSURE COMPREHENSIVE COVERAGE:
   - Write multiple tests for functions with branching logic
   - Test all conditional branches (if/else paths)
   - Test exception handling with pytest.raises()
   - Include parameterized tests for functions that handle different input types

Remember: The goal is to INCREASE code coverage, which requires tests to execute the actual code paths, not just mock them.

Here's an example of a good test vs. a poor test for coverage:

POOR (won't improve coverage):
```python
def test_function_called():
    # This only verifies the function was called, but doesn't test its logic
    with mock.patch('module.function') as mock_func:
        result = some_code_that_calls_function()
        mock_func.assert_called_once()
```

GOOD (improves coverage):
```python
def test_function_normal_case():
    # This runs the actual code and verifies results
    input_value = "test input"
    result = function(input_value)
    assert result == expected_output
    
def test_function_edge_case():
    # This tests another branch in the code
    input_value = ""
    result = function(input_value) 
    assert result == expected_edge_case_output
    
def test_function_error_handling():
    # This tests exception handling
    with pytest.raises(ValueError):
        function(None)
```
"""

def normalize_module_path(module_path):
    """Normalize module path to match Python import conventions."""
    # Replace hyphens with underscores for proper Python imports
    normalized_path = module_path.replace('-', '_')
    
    # Ensure path has galaxy_ng prefix if needed
    if not normalized_path.startswith('galaxy_ng/'):
        normalized_path = f'galaxy_ng/{normalized_path}'
    
    return normalized_path

def get_module_import_path(module_path):
    """Convert file path to Python import path."""
    import_path = normalize_module_path(module_path).replace('/', '.').replace('.py', '')
    return import_path

def fix_module_path(filename):
    """
    Fix the module path to match the actual repository structure.
    Coverage paths like 'app/utils/galaxy.py' should be mapped to 'galaxy_ng/app/utils/galaxy.py'
    """
    # Normalize path - replace hyphens with underscores
    filename = filename.replace('-', '_')
    
    # If path already starts with galaxy_ng/, return as is
    if filename.startswith('galaxy_ng/'):
        return filename
    
    # Default to adding galaxy_ng/ prefix if not already prefixed
    return os.path.join('galaxy_ng', filename)

def read_file_content(file_path):
    """Read the content of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def locate_module_file(module_path):
    """
    Try to locate a module file using different approaches.
    Returns the actual file path if found, or None if not found.
    """
    # Try the exact path first
    if os.path.exists(module_path):
        return module_path
    
    # Try the normalized path (with galaxy_ng prefix)
    fixed_path = fix_module_path(module_path)
    if os.path.exists(fixed_path):
        return fixed_path
    
    # Try alternative names (handle hyphen/underscore variations)
    base_name = os.path.basename(module_path)
    dir_path = os.path.dirname(fixed_path)
    
    # If filename has hyphens, try with underscores
    if '-' in base_name:
        alt_name = base_name.replace('-', '_')
        alt_path = os.path.join(dir_path, alt_name)
        if os.path.exists(alt_path):
            return alt_path
    
    # If filename has underscores, try with hyphens
    if '_' in base_name:
        alt_name = base_name.replace('_', '-')
        alt_path = os.path.join(dir_path, alt_name)
        if os.path.exists(alt_path):
            return alt_path
    
    # Try a glob search in the directory
    import glob
    glob_pattern = os.path.join(dir_path, f"*{os.path.splitext(base_name)[0]}*{os.path.splitext(base_name)[1]}")
    matches = glob.glob(glob_pattern)
    if matches:
        return matches[0]
    
    # If all else fails, return None
    return None

def get_existing_tests(module_path):
    """Find existing test files for the given module."""
    try:
        # Ensure we're working with the correct module path
        fixed_path = fix_module_path(module_path)
        
        # Determine potential test locations
        module_dir = os.path.dirname(fixed_path)
        module_name = os.path.basename(fixed_path).replace('.py', '')
        
        # Common test file patterns
        test_patterns = [
            os.path.join(module_dir, 'tests', f'test_{module_name}.py'),
            os.path.join(module_dir, 'tests', module_name, 'test_*.py'),
            os.path.join('galaxy_ng', 'tests', module_dir.replace('galaxy_ng/', ''), f'test_{module_name}.py'),
            os.path.join('galaxy_ng', 'tests', 'unit', f'test_{module_name}.py'),
        ]
        
        existing_tests = []
        for pattern in test_patterns:
            if '*' in pattern:
                # Handle wildcard patterns
                base_dir = os.path.dirname(pattern)
                if os.path.exists(base_dir):
                    for file in os.listdir(base_dir):
                        if file.startswith('test_') and file.endswith('.py'):
                            existing_tests.append(os.path.join(base_dir, file))
            elif os.path.exists(pattern):
                existing_tests.append(pattern)
        
        return existing_tests
    except Exception as e:
        print(f"Error finding existing tests: {e}")
        return []

def create_test_template(module_path, module_import_path):
    """Create a robust test template that minimizes mocking and focuses on real code execution."""
    
    return f'''import os
import sys
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

# Import the actual module being tested - don't mock it
from {module_import_path} import *

# Set up fixtures for common dependencies

@pytest.fixture
def mock_request():
    """Fixture for a mocked request object."""
    return mock.MagicMock(
        user=mock.MagicMock(
            username="test_user",
            is_superuser=False,
            is_authenticated=True
        )
    )

@pytest.fixture
def mock_superuser():
    """Fixture for a superuser request."""
    return mock.MagicMock(
        username="admin_user",
        is_superuser=True,
        is_authenticated=True
    )

# Add test functions below
# Remember to test different cases and execution paths to maximize coverage
'''

def balance_parentheses(content):
    """
    Automatically balance parentheses, brackets, and braces in code.
    Uses a stack-based approach to find and fix mismatches.
    """
    lines = content.splitlines()
    stack = []
    line_brackets = {}  # Track brackets by line
    
    # First pass: mark all opening brackets and their lines
    for i, line in enumerate(lines):
        line_stack = []
        for j, char in enumerate(line):
            if char in '({[':
                stack.append((char, i, j))
                line_stack.append((char, j))
            elif char in ')}]':
                if stack and ((char == ')' and stack[-1][0] == '(') or
                              (char == '}' and stack[-1][0] == '{') or
                              (char == ']' and stack[-1][0] == '[')):
                    stack.pop()
                    if line_stack:
                        line_stack.pop()
                else:
                    # Unmatched closing bracket - ignore for now
                    pass
        
        # Store brackets that weren't closed on this line
        if line_stack:
            line_brackets[i] = line_stack
    
    # Second pass: add missing closing brackets at the end of appropriate lines
    if stack:
        # Group by line
        by_line = {}
        for bracket, line_num, _ in stack:
            by_line.setdefault(line_num, []).append(bracket)
        
        # Get corresponding closing brackets
        closing = {
            '(': ')',
            '{': '}',
            '[': ']'
        }
        
        # Fix lines with unclosed brackets
        for i, brackets in sorted(by_line.items(), reverse=True):
            # Check if next line has a closing bracket matching our opening
            if i < len(lines) - 1 and any(c in closing.values() for c in lines[i+1]):
                continue  # Skip - next line probably has closing bracket
                
            # Add closing brackets in reverse order
            to_close = ''.join(closing[b] for b in brackets[::-1])
            
            # Only add if the line doesn't already end with a bracket
            if not lines[i].rstrip().endswith(tuple(closing.values())):
                lines[i] = lines[i] + to_close
    
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

def fix_test_definitions(content):
    """Fix test function definitions with syntax errors."""
    def_pattern = r'def\s+(test_\w+)\s*(?!\()'
    fixed_content = re.sub(def_pattern, r'def \1()', content)
    
    # Fix test definitions that might be missing a colon at the end
    def_pattern2 = r'def\s+(test_\w+)(\([^)]*\))\s*(?!:)'
    fixed_content = re.sub(def_pattern2, r'def \1\2:', fixed_content)
    
    return fixed_content

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

def validate_and_fix_test(test_content, module_path):
    """Validate and fix common test issues."""
    
    # Apply fixes in sequence
    fixed_content = test_content
    
    # 1. Fix import paths (replace hyphens with underscores)
    fixed_content = re.sub(
        r'from galaxy_ng\.([^-\s]+)-([^-\s]+)', 
        r'from galaxy_ng.\1_\2', 
        fixed_content
    )
    fixed_content = re.sub(
        r'import galaxy_ng\.([^-\s]+)-([^-\s]+)', 
        r'import galaxy_ng.\1_\2', 
        fixed_content
    )
    
    # 2. Fix factory imports
    fixed_content = fix_import_statements(fixed_content)
    
    # 3. Fix test function definitions
    fixed_content = fix_test_definitions(fixed_content)
    
    # 4. Fix annotation syntax
    fixed_content = fix_annotation_syntax(fixed_content)
    
    # 5. Add handling for special modules
    module_name = os.path.basename(module_path)
    if module_name == '__init__.py' or 'social/__init__' in module_path:
        fixed_content = handle_special_modules(fixed_content, module_path)
    
    # 6. Balance parentheses, brackets, and braces
    fixed_content = balance_parentheses(fixed_content)
    
    # 7. Fix advanced syntax errors
    fixed_content = fix_advanced_syntax_errors(fixed_content)
    
    # 8. Make sure module is imported
    module_import_path = get_module_import_path(module_path)
    if module_import_path not in fixed_content:
        import_statement = f"\n# Import module being tested\ntry:\n    from {module_import_path} import *\nexcept (ImportError, ModuleNotFoundError):\n    # Mock module if import fails\n    sys.modules['{module_import_path}'] = mock.MagicMock()\n\n"
        if 'import pytest' in fixed_content:
            fixed_content = fixed_content.replace('import pytest', 'import pytest\nimport sys' + import_statement)
        else:
            # Add at the top after environment setup
            fixed_content = create_test_template(module_path) + fixed_content
    
    # 9. Ensure django.setup() is included
    if 'django.setup()' not in fixed_content:
        fixed_content = create_test_template(module_path) + fixed_content
    
    # 10. Verify syntax with ast parse
    try:
        ast.parse(fixed_content)
    except SyntaxError as e:
        print(f"Warning: Syntax error remains in fixed content: {e}")
        # Mark file as needing manual review
        fixed_content = f"# WARNING: This file has syntax errors that need manual review: {e}\n" + fixed_content
    
    return fixed_content

def generate_test_with_ai(api_key, module_path, module_content, existing_tests=None, model="Meta-Llama-3.1-8B-Instruct"):
    """Use SambaNova AI to generate test code."""
    base_url = "https://api.sambanova.ai/v1"
    endpoint = f"{base_url}/chat/completions"
    
    # Get updated system prompt
    system_prompt = update_system_prompt()
    
    # Prepare existing test content if available
    existing_test_content = ""
    if existing_tests:
        for test_file in existing_tests:
            content = read_file_content(test_file)
            if content:
                existing_test_content += f"\n# Existing test file: {test_file}\n{content}\n"
    
    # Prepare imports info by scanning the module content
    imports = re.findall(r'^(?:from|import)\s+.*', module_content, re.MULTILINE)
    imports_info = "\n".join(imports) if imports else "No explicit imports found"
    
    # Determine the test file path to generate
    fixed_path = fix_module_path(module_path)
    module_dir = os.path.dirname(fixed_path)
    module_name = os.path.basename(fixed_path).replace('.py', '')
    test_dir = os.path.join('galaxy_ng', 'tests', 'unit', 'ai_generated')
    
    # Make sure module_name doesn't have hyphens (problematic for imports)
    module_name = module_name.replace('-', '_')
    test_file_path = os.path.join(test_dir, f'test_{module_name}.py')
    
    # Build user prompt
    user_prompt = f"""I need pytest tests with HIGH CODE COVERAGE for the following Python module from the Galaxy NG project.

MODULE PATH: {fixed_path}

MODULE IMPORTS:
{imports_info}

MODULE CODE:
```python
{module_content}
```

{"EXISTING TEST FILES:" if existing_test_content else ""}
{existing_test_content if existing_test_content else ""}

Please generate a COMPLETE test file that will be saved to: {test_file_path}

IMPORTANT COVERAGE GUIDELINES:
1. Your tests should EXECUTE THE ACTUAL CODE to increase coverage metrics
2. DON'T mock the module under test - mock only external dependencies
3. TEST ALL LOGICAL BRANCHES including error cases, edge conditions and happy paths
4. Include MULTIPLE TEST CASES for functions with branching logic
5. TEST THE ACTUAL BEHAVIOR AND OUTPUTS of functions, not just that they were called
6. Use assertions that verify return values and side effects

TESTING STRUCTURE:
1. Include proper Django environment setup at the top of the file
2. Create meaningful pytest fixtures for common test data
3. Follow test function naming convention: test_function_name_scenario()
4. Group tests logically by function or behavior
5. Use pytest.mark.parametrize for testing similar behaviors with different inputs

EXAMPLES OF GOOD COVERAGE TESTS:
```python
def test_uuid_to_int_converts_valid_uuid():
    # Direct test of behavior with assertion on result
    test_uuid = "12345678-1234-1234-1234-123456789012"
    result = uuid_to_int(test_uuid)
    assert result == 0x123456781234123412341234123456789012

def test_uuid_to_int_raises_error_for_invalid_uuid():
    # Tests error branch
    with pytest.raises(ValueError):
        uuid_to_int("invalid-uuid")
    
@pytest.mark.parametrize("input_value,expected", [
    ("value1", "result1"),
    ("value2", "result2"),
    ("", "empty_result")
])
def test_function_with_different_inputs(input_value, expected):
    # Tests multiple scenarios for better coverage
    assert function(input_value) == expected
```

Return ONLY the Python test code without explanations or markdown formatting.
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "temperature": 0.1,  # Low temperature for more deterministic output
        "top_p": 0.1,  # Lower top_p for more focused output
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                test_code = result["choices"][0]["message"]["content"]
                # Clean up any markdown code block formatting the AI might have included
                test_code = re.sub(r'```python\s*', '', test_code)
                test_code = re.sub(r'```\s*$', '', test_code)
                
                # Apply validation and fixes to the generated test code
                test_code = validate_and_fix_test(test_code, module_path)
                
                return test_code
            else:
                print(f"Unexpected API response format: {result}")
                
        except requests.exceptions.RequestException as e:
            print(f"API request error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"Unexpected error in test generation: {e}")
            traceback.print_exc()
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        
    return None

def save_test_file(test_path, test_content):
    """Save the generated test to a file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        
        # Check if file already exists
        if os.path.exists(test_path):
            # Create backup if needed
            backup_path = f"{test_path}.bak"
            os.rename(test_path, backup_path)
            print(f"Created backup of existing test file: {backup_path}")
        
        # Final validation before saving
        try:
            ast.parse(test_content)
        except SyntaxError as e:
            print(f"Warning: Syntax error in generated test: {e}")
            # Add comment at the top to indicate it needs fixing
            test_content = f"# WARNING: This file has syntax errors that need to be fixed: {e}\n" + test_content
        
        # Write the new test file
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        print(f"Successfully wrote test file to {test_path}")
        return True
    except Exception as e:
        print(f"Error saving test file: {e}")
        traceback.print_exc()
        return False

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Generate tests using AI for low-coverage modules')
    parser.add_argument('--candidates', required=True, help='Path to the JSON file with test candidates')
    parser.add_argument('--api-key', help='SambaNova API key (falls back to SAMBANOVA_API_KEY env var)')
    parser.add_argument('--model', default='Meta-Llama-3.1-8B-Instruct', help='AI model to use')
    parser.add_argument('--output-dir', default='generated_tests', help='Directory to store generated tests')
    parser.add_argument('--limit', type=int, default=5, help='Maximum number of modules to process')
    
    args = parser.parse_args()

    # Get API key from args or environment
    api_key = args.api_key or os.environ.get('SAMBANOVA_API_KEY')
    if not api_key:
        print("Error: SambaNova API key not provided. Use --api-key or set SAMBANOVA_API_KEY environment variable.")
        sys.exit(1)

    # Read candidates file
    try:
        with open(args.candidates, 'r') as f:
            candidates = json.load(f)
    except Exception as e:
        print(f"Error reading candidates file: {e}")
        sys.exit(1)

    # Limit the number of candidates to process
    candidates = candidates[:args.limit]

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Process each candidate
    results = []
    for i, candidate in enumerate(candidates, 1):
        filename = candidate['filename']
        
        # Normalize filename (replace hyphens with underscores)
        normalized_filename = filename.replace('-', '_')
        if normalized_filename != filename:
            print(f"Normalized filename from {filename} to {normalized_filename}")
            filename = normalized_filename
        
        print(f"\n[{i}/{len(candidates)}] Processing {filename} (Coverage: {candidate['coverage_pct']:.2f}%)")
        
        # Try to locate the module file
        actual_file_path = locate_module_file(filename)
        if not actual_file_path:
            print(f"Skipping {filename} - could not locate file")
            results.append({
                'filename': filename,
                'status': 'error',
                'message': 'Could not locate file'
            })
            continue
        
        print(f"Found file at: {actual_file_path}")
        
        # Read the module content
        module_content = read_file_content(actual_file_path)
        if not module_content:
            print(f"Skipping {filename} - could not read file")
            results.append({
                'filename': filename,
                'status': 'error',
                'message': 'Could not read file'
            })
            continue
        
        # Find existing tests
        existing_tests = get_existing_tests(filename)
        if existing_tests:
            print(f"Found {len(existing_tests)} existing test files:")
            for test in existing_tests:
                print(f"  - {test}")
        
        # Generate test code
        print(f"Generating tests for {filename}...")
        test_code = generate_test_with_ai(api_key, filename, module_content, existing_tests, args.model)
        
        if not test_code:
            print(f"Failed to generate test code for {filename}")
            results.append({
                'filename': filename,
                'status': 'error',
                'message': 'AI generation failed'
            })
            continue
        
        # Determine the test file path
        module_name = os.path.basename(filename).replace('.py', '').replace('-', '_')
        test_dir = os.path.join('galaxy_ng', 'tests', 'unit', 'ai_generated')
        
        # Create directory structure if it doesn't exist
        os.makedirs(test_dir, exist_ok=True)
        
        test_file_path = os.path.join(test_dir, f'test_{module_name}.py')
        
        # Also save a copy in our output directory for reference
        output_path = os.path.join(args.output_dir, f'test_{filename.replace("/", "_")}')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        # Save the actual test file
        if save_test_file(test_file_path, test_code):
            print(f"Successfully generated test file: {test_file_path}")
            results.append({
                'filename': filename,
                'status': 'success',
                'test_file': test_file_path,
                'reference_file': output_path
            })
        else:
            print(f"Failed to save test file for {filename}")
            results.append({
                'filename': filename,
                'status': 'error',
                'message': 'Failed to save test file'
            })

    # Save results summary
    results_file = os.path.join(args.output_dir, 'generation_results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\nTest generation summary: {success_count}/{len(results)} successful")
    print(f"Results saved to {results_file}")

if __name__ == "__main__":
    main()