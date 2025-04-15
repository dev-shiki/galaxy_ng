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
from pathlib import Path
import re

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

The code is from the Galaxy NG project, an Ansible Galaxy server built on Django and Django REST Framework.
"""

def fix_module_path(filename):
    """
    Fix the module path to match the actual repository structure.
    Coverage paths like 'app/utils/galaxy.py' should be mapped to 'galaxy_ng/app/utils/galaxy.py'
    """
    # List of possible prefix directories based on the repo structure
    possible_prefixes = ['galaxy_ng/', 'galaxy-operator/']
    
    # If path already starts with one of our known directories, return as is
    for prefix in possible_prefixes:
        if filename.startswith(prefix):
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
2. Properly import all necessary modules
3. Include appropriate fixtures and mocks
4. Achieve high code coverage by testing all functions and methods
5. Test edge cases and error conditions
6. Follow Django and pytest best practices

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
        module_name = os.path.basename(fixed_path).replace('.py', '')
        test_dir = os.path.join(module_dir, 'tests')
        if not os.path.exists(test_dir):
            test_dir = os.path.join('galaxy_ng', 'tests', module_dir.replace('galaxy_ng/', ''))
        
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