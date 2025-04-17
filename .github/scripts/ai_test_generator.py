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
from pathlib import Path

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 60  # seconds

# Default system prompt for AI test generation
DEFAULT_SYSTEM_PROMPT = """You are an expert Python developer specializing in writing pytest tests for Django applications.
Your task is to analyze the provided code and generate comprehensive pytest tests that:
1. Achieve high code coverage
2. Test all important functionality and edge cases
3. Use appropriate mocks and fixtures
4. Follow best practices for pytest and Django testing

CRITICAL RULES:
1. DO NOT use hyphens (-) in any import statements or module names - always use underscores (_)
2. DO NOT assume 'factories' module exists - use mock.MagicMock to create factory mocks
3. DO NOT import modules that might not exist - use try/except for imports
4. ALWAYS check your Python syntax - ensure all function definitions have proper parentheses and colons
5. ALWAYS use proper test function naming: def test_something():
6. ALWAYS include proper Django environment setup at the top of each test file

The code is from the Galaxy NG project, an Ansible Galaxy server built on Django and Django REST Framework.
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

def validate_and_fix_test(test_content, module_path):
    """Validate and fix common test issues."""
    
    # 1. Fix import paths (replace hyphens with underscores)
    fixed_content = re.sub(
        r'from galaxy_ng\.([^-\s]+)-([^-\s]+)', 
        r'from galaxy_ng.\1_\2', 
        test_content
    )
    fixed_content = re.sub(
        r'import galaxy_ng\.([^-\s]+)-([^-\s]+)', 
        r'import galaxy_ng.\1_\2', 
        fixed_content
    )
    
    # 2. Check for syntax errors
    try:
        ast.parse(fixed_content)
    except SyntaxError as e:
        line_no = e.lineno if hasattr(e, 'lineno') else 0
        print(f"Syntax error at line {line_no}: {e}")
        
        # Extract problematic lines and try to fix
        lines = fixed_content.splitlines()
        if 0 < line_no <= len(lines):
            # Common fixes for syntax errors
            if 'def test_' in lines[line_no-1] and not lines[line_no-1].strip().endswith(':'):
                if '(' not in lines[line_no-1]:
                    lines[line_no-1] = lines[line_no-1] + '():'
                else:
                    lines[line_no-1] = lines[line_no-1] + ':'
                fixed_content = '\n'.join(lines)
    
    # 3. Add mock for factories if referenced but not defined
    if "factories" in fixed_content and "factories = mock.MagicMock()" not in fixed_content:
        factories_mock = '\n# Mock for factories\nfactories = mock.MagicMock()\nfactories.UserFactory = mock.MagicMock()\nfactories.GroupFactory = mock.MagicMock()\nfactories.NamespaceFactory = mock.MagicMock()\n'
        if 'import mock' in fixed_content:
            fixed_content = fixed_content.replace('import mock', 'import mock' + factories_mock)
        else:
            fixed_content = 'import mock\n' + factories_mock + fixed_content
    
    # 4. Fix module imports for the specific module
    module_import_path = get_module_import_path(module_path)
    if module_import_path not in fixed_content:
        import_statement = f"\n# Import module being tested\ntry:\n    from {module_import_path} import *\nexcept (ImportError, ModuleNotFoundError):\n    # Mock module if import fails\n    sys.modules['{module_import_path}'] = mock.MagicMock()\n\n"
        if 'import pytest' in fixed_content:
            fixed_content = fixed_content.replace('import pytest', 'import pytest\nimport sys' + import_statement)
        else:
            # Add at the top after environment setup
            fixed_content = create_test_template(module_path) + fixed_content
    
    return fixed_content

def generate_test_with_ai(api_key, module_path, module_content, existing_tests=None, model="Qwen2.5-Coder-32B-Instruct"):
    """Use SambaNova AI to generate test code."""
    base_url = "https://api.sambanova.ai/v1"
    endpoint = f"{base_url}/chat/completions"
    
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

REQUIRED TEST TEMPLATE:
```python
import os
import sys
import re
import pytest
from unittest import mock

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

# [Add other imports needed for testing]

# [Add your fixtures here]

# [Add your test classes and functions here]
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
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
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
                return test_code
            else:
                print(f"Unexpected API response format: {result}")
                
        except requests.exceptions.RequestException as e:
            print(f"API request error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
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
        
        # Write the new test file
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        print(f"Successfully wrote test file to {test_path}")
        return True
    except Exception as e:
        print(f"Error saving test file: {e}")
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