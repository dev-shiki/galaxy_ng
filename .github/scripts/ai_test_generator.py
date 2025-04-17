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
    """Create a comprehensive system prompt for AI test generation."""
    return """You are an expert Python developer specializing in writing pytest tests for Django applications.
Your task is to analyze the provided code and generate comprehensive pytest tests that follow these strict rules:

CRITICAL GUIDELINES FOR GENERATING VALID TESTS:

1. IMPORTS AND DEPENDENCIES:
   - NEVER import 'factories' modules directly (they don't exist): ❌ `from galaxy_ng.social import factories`
   - NEVER use incomplete imports: ❌ `from galaxy_module`
   - ALWAYS mock external dependencies: ✅ `module = mock.MagicMock()`
   - ALWAYS use try/except for potentially problematic imports:
     ```python
     try:
         from galaxy_ng.app.utils.galaxy import get_collection_download_url
     except ImportError:
         # Mock the function if import fails
         get_collection_download_url = mock.MagicMock()
     ```

2. MOCKING FACTORIES:
   - ALWAYS mock factories instead of importing them:
     ```python
     # Create mock factories
     factories = mock.MagicMock()
     factories.UserFactory = mock.MagicMock(return_value=mock.MagicMock(username="test_user"))
     factories.GroupFactory = mock.MagicMock()
     factories.NamespaceFactory = mock.MagicMock()
     factories.CollectionFactory = mock.MagicMock()
     ```

3. SYNTAX AND STRUCTURE:
   - ALWAYS use proper function definitions: ✅ `def test_something():`
   - ALWAYS balance all parentheses, brackets, and braces
   - ALWAYS use proper indentation and formatting
   - NEVER leave function calls with unclosed parentheses

4. DJANGO ENVIRONMENT SETUP:
   - ALWAYS include this exact setup at the top of each test file:
     ```python
     import os
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
     ```

5. SPECIAL MODULE HANDLING:
   - For __init__.py files, use system module mocking:
     ```python
     # Mock modules accessed in __init__.py
     import sys
     social_auth = mock.MagicMock()
     sys.modules['galaxy_ng.social.auth'] = social_auth
     ```
   - For Django model tests, use proper model mocking:
     ```python
     # Mock Django models
     model_mock = mock.MagicMock()
     model_mock.objects.get.return_value = mock.MagicMock(name="mocked_object")
     model_mock.DoesNotExist = Exception
     ```

6. FILE NAMING AND MODULE REFERENCES:
   - NEVER use hyphens (-) in import statements or file references - always use underscores (_)
   - Normalize all module paths: ✅ `galaxy_ng.app.utils.galaxy` ❌ `galaxy_ng.app.utils-galaxy`

7. TESTING APPROACH:
   - Create separate test functions for each method/function being tested
   - Include tests for success cases, error cases, and edge cases
   - Use descriptive test names that indicate what's being tested
   - Prefer focused tests that test one thing well over large complex tests

The code is from the Galaxy NG project, which is an Ansible Galaxy server built on Django and Django REST Framework.
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

def create_test_template(module_path):
    """Create a robust test template with proper imports."""
    module_import_path = get_module_import_path(module_path)
    
    return f'''import os
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

# Safe imports with fallbacks for the module being tested
try:
    from {module_import_path} import *
except (ImportError, ModuleNotFoundError) as e:
    print(f"Warning: Could not import {module_import_path}: {{e}}")
    # Mock the module since we can't import it directly
    sys.modules['{module_import_path}'] = mock.MagicMock()

# Mock commonly used dependencies
class MockFactory(mock.MagicMock):
    """Generic factory mock for testing."""
    @classmethod
    def create(cls, **kwargs):
        return mock.MagicMock(**kwargs)
        
# Use this if factories import fails
if 'factories' not in globals():
    factories = mock.MagicMock()
    factories.UserFactory = MockFactory
    factories.GroupFactory = MockFactory
    factories.NamespaceFactory = MockFactory
    factories.CollectionFactory = MockFactory
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
    
    # 4. Add handling for special modules
    module_name = os.path.basename(module_path)
    if module_name == '__init__.py' or 'social/__init__' in module_path:
        fixed_content = handle_special_modules(fixed_content, module_path)
    
    # 5. Balance parentheses, brackets, and braces
    fixed_content = balance_parentheses(fixed_content)
    
    # 6. Add mock for factories if referenced but not defined
    if "factories" in fixed_content and "factories = mock.MagicMock()" not in fixed_content:
        factories_mock = '\n# Mock for factories\nfactories = mock.MagicMock()\nfactories.UserFactory = mock.MagicMock()\nfactories.GroupFactory = mock.MagicMock()\nfactories.NamespaceFactory = mock.MagicMock()\n'
        if 'import mock' in fixed_content:
            fixed_content = fixed_content.replace('import mock', 'import mock' + factories_mock)
        else:
            fixed_content = 'import mock\n' + factories_mock + fixed_content
    
    # 7. Fix module imports for the specific module
    module_import_path = get_module_import_path(module_path)
    if module_import_path not in fixed_content:
        import_statement = f"\n# Import module being tested\ntry:\n    from {module_import_path} import *\nexcept (ImportError, ModuleNotFoundError):\n    # Mock module if import fails\n    sys.modules['{module_import_path}'] = mock.MagicMock()\n\n"
        if 'import pytest' in fixed_content:
            fixed_content = fixed_content.replace('import pytest', 'import pytest\nimport sys' + import_statement)
        else:
            # Add at the top after environment setup
            fixed_content = create_test_template(module_path) + fixed_content
    
    # 8. Ensure django.setup() is included
    if 'django.setup()' not in fixed_content:
        fixed_content = create_test_template(module_path) + fixed_content
    
    # 9. Verify syntax with ast parse
    try:
        ast.parse(fixed_content)
    except SyntaxError as e:
        print(f"Warning: Syntax error remains in fixed content: {e}")
        # Mark file as needing manual review
        fixed_content = f"# WARNING: This file has syntax errors that need manual review: {e}\n" + fixed_content
    
    return fixed_content

def generate_test_with_ai(api_key, module_path, module_content, existing_tests=None, model="Qwen2.5-Coder-32B-Instruct"):
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
    test_dir = os.path.join(module_dir, 'tests')
    if not os.path.exists(test_dir):
        test_dir = os.path.join('galaxy_ng', 'tests', module_dir.replace('galaxy_ng/', ''))
    
    # Make sure module_name doesn't have hyphens (problematic for imports)
    module_name = module_name.replace('-', '_')
    test_file_path = os.path.join(test_dir, f'test_{module_name}.py')
    
    # Build user prompt
    user_prompt = f"""I need comprehensive pytest tests for the following Python module from the Galaxy NG project.

MODULE PATH: {fixed_path}

MODULE IMPORTS:
{imports_info}

MODULE CODE:
```python
{module_content}
```

{"EXISTING TEST FILES:" if existing_test_content else ""}
{existing_test_content if existing_test_content else ""}

Please generate a complete test file that will:
1. Be saved to: {test_file_path}
2. Include proper Django environment setup at the beginning of the file
3. Include all necessary imports and mocks
4. Test each function/method with multiple test cases
5. Achieve high code coverage by testing all code paths, including error conditions
6. Follow Django and pytest best practices
7. Use clear, descriptive test names

CRITICAL REQUIREMENTS:
1. DO NOT use hyphens (-) in import statements or module references - always use underscores (_)
2. DO NOT assume 'factories' module exists - use mock.MagicMock() to create mock factories
3. Make sure all test function definitions end with colons and have proper parentheses: def test_something():
4. ALWAYS balance parentheses, brackets, and braces in your code
5. For init.py files, use special module mocking to prevent import errors

Please include this exact Django environment setup:
```python
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
    parser.add_argument('--model', default='Qwen2.5-Coder-32B-Instruct', help='AI model to use')
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
        
        # Fix the path to match repository structure
        fixed_path = fix_module_path(filename)
        print(f"Looking for file at: {fixed_path}")
        
        # Read the module content
        module_content = read_file_content(fixed_path)
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
        module_dir = os.path.dirname(fixed_path)
        module_name = os.path.basename(fixed_path).replace('.py', '').replace('-', '_')
        
        # First try module's own tests directory
        test_dir = os.path.join(module_dir, 'tests')
        if not os.path.exists(test_dir):
            # Then try a common tests directory structure
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