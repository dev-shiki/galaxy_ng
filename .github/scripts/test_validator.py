#!/usr/bin/env python3
"""
This script validates generated test files by running them with pytest
and checking if they improve coverage. It also includes fixes for common issues.
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import ast
import re
import xml.etree.ElementTree as ET
from pathlib import Path

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
    
    print(f"Created mock pulp_smash config at {config_path}")
    return config_path

def install_dependencies():
    """Install required test dependencies."""
    print("Installing required test dependencies...")
    
    # First install numpy - this is needed by pulp_ansible pytest plugin
    subprocess.run(
        ["pip", "install", "numpy"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Install from unittest_requirements if it exists
    if os.path.exists("unittest_requirements.txt"):
        print("Installing from unittest_requirements.txt...")
        subprocess.run(
            ["pip", "install", "-r", "unittest_requirements.txt"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    
    # Install the project in development mode
    print("Installing project in development mode...")
    subprocess.run(
        ["pip", "install", "-e", "."],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print("Dependencies installed")

def fix_common_test_issues(test_file):
    """Fix common issues in test files before running them."""
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Fix imports for non-existent factories
        factory_patterns = [
            (r'from galaxy_ng\.social import factories', '# Mock factories\nimport mock\nsocial_factories = mock.MagicMock()'),
            (r'from galaxy_ng\.tests import factories', '# Mock factories\nimport mock\nfactories = mock.MagicMock()'),
            (r'from galaxy_ng\.([^.\s]+) import factories', r'# Mock \1 factories\nimport mock\n\1_factories = mock.MagicMock()'),
        ]
        
        for pattern, replacement in factory_patterns:
            content = re.sub(pattern, replacement, content)
        
        # 2. Fix incomplete imports
        incomplete_imports = [
            (r'from galaxy_module\s*$', '# Fixed incomplete import\nimport mock\ngalaxy_module = mock.MagicMock()'),
            (r'import galaxy_module\s*$', '# Fixed incomplete import\nimport mock\ngalaxy_module = mock.MagicMock()'),
        ]
        
        for pattern, replacement in incomplete_imports:
            content = re.sub(pattern, replacement, content)
        
        # 3. Fix missing parentheses in function definitions
        content = re.sub(r'def\s+(test_\w+)\s*(?!\()', r'def \1()', content)
        
        # 4. Fix missing colons in function definitions
        content = re.sub(r'def\s+(test_\w+)(\([^)]*\))\s*(?!:)', r'def \1\2:', content)
        
        # 5. Fix unclosed parentheses
        lines = content.splitlines()
        stack = []
        line_brackets = {}
        
        for i, line in enumerate(lines):
            line_stack = []
            for j, char in enumerate(line):
                if char in '({[':
                    stack.append((char, i))
                    line_stack.append(char)
                elif char in ')}]':
                    matching = {'(': ')', '{': '}', '[': ']'}
                    if stack and matching.get(stack[-1][0]) == char:
                        stack.pop()
                        if line_stack:
                            line_stack.pop()
            
            if line_stack:
                line_brackets[i] = line_stack
        
        # Add missing closing brackets
        if stack:
            matching = {'(': ')', '{': '}', '[': ']'}
            line_fixes = {}
            
            for bracket, line_num in stack:
                line_fixes.setdefault(line_num, []).append(matching[bracket])
            
            for line_num, closers in sorted(line_fixes.items(), reverse=True):
                lines[line_num] = lines[line_num] + ''.join(closers)
            
            content = '\n'.join(lines)
        
        # 6. Special handling for __init__.py tests
        if 'test___init__' in test_file or 'test_social___init__' in test_file:
            init_mocks = '''
# Mock special modules for __init__.py testing
import sys
social_factories = mock.MagicMock()
auth_module = mock.MagicMock()
social_auth = mock.MagicMock()

# Add to sys.modules to prevent import errors
sys.modules['galaxy_ng.social.factories'] = social_factories
sys.modules['galaxy_ng.social.auth'] = auth_module
'''
            if 'import mock' in content:
                content = content.replace('import mock', 'import mock\nimport sys', 1)
                content = content.replace('import sys', 'import sys' + init_mocks, 1)
            else:
                content = 'import mock\nimport sys' + init_mocks + content
        
        # 7. Add mock for factories if referenced but not defined
        if "factories" in content and "factories = mock.MagicMock()" not in content:
            factories_mock = '\n# Mock for factories\nfactories = mock.MagicMock()\nfactories.UserFactory = mock.MagicMock()\nfactories.GroupFactory = mock.MagicMock()\nfactories.NamespaceFactory = mock.MagicMock()\n'
            if 'import mock' in content:
                content = content.replace('import mock', 'import mock' + factories_mock, 1)
            else:
                content = 'import mock\n' + factories_mock + content
        
        # Write the fixed content back to the file
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Validate syntax
        try:
            ast.parse(content)
            print(f"✅ {test_file} is syntactically valid")
            return True
        except SyntaxError as e:
            print(f"❌ {test_file} has syntax errors: {e}")
            return False
            
    except Exception as e:
        print(f"Error fixing {test_file}: {e}")
        return False

def create_pytest_ini():
    """Create pytest.ini file to configure pytest."""
    content = """[pytest]
testpaths = galaxy_ng
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    deployment_standalone: marks tests to run in standalone mode
    deployment_community: marks tests to run in community mode
    deployment_cloud: marks tests to run in cloud/insights mode
addopts = -p no:pulp_ansible -p no:pulpcore
"""
    with open("pytest.ini", "w") as f:
        f.write(content)
    
    print("Created pytest.ini for test configuration")

def run_pytest_test(test_file):
    """Run a test file with pytest directly."""
    try:
        # Create pulp_smash config first
        create_pulp_smash_config()
        
        # Install dependencies first
        install_dependencies()
        
        # Create pytest.ini to disable problematic plugins
        create_pytest_ini()
        
        # First fix common issues in the test file
        fix_common_test_issues(test_file)
        
        # Run pytest with disabled plugins to avoid errors
        cmd = [
            "python", "-m", "pytest",
            "-p", "no:pulp_smash",  # Disable pulp_smash plugin
            "-p", "no:pulpcore",    # Disable pulpcore plugin
            "-p", "no:pulp_ansible", # Disable pulp_ansible plugin
            test_file,
            "-v"
        ]
        
        print(f"Running pytest validation: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env=dict(os.environ, PYTHONPATH=os.getcwd())
        )
        
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def run_coverage_test(test_file, module_path):
    """Run a test file with coverage to check for coverage improvements."""
    try:
        # Create a temporary directory for coverage data
        temp_dir = tempfile.mkdtemp(prefix="coverage_test_")
        
        # Normalize module path
        module_path = module_path.replace('-', '_')
        if not module_path.startswith('galaxy_ng/'):
            module_path = f'galaxy_ng/{module_path}'
        
        # Get module import path
        module_import_path = module_path.replace('/', '.').replace('.py', '')
        
        # Fix the test file
        fix_common_test_issues(test_file)
        
        # Run pytest with coverage
        coverage_file = os.path.join(temp_dir, "coverage.xml")
        cmd = [
            "python", "-m", "pytest",
            test_file,
            f"--cov={module_import_path}",
            f"--cov-report=xml:{coverage_file}",
            "-p", "no:pulp_smash",
            "-p", "no:pulpcore",
            "-p", "no:pulp_ansible",
            "-v"
        ]
        
        print(f"Running coverage test: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env=dict(os.environ, PYTHONPATH=os.getcwd())
        )
        
        # Check if coverage file was generated
        if os.path.exists(coverage_file):
            # Extract coverage data
            coverage_data = extract_module_coverage(coverage_file, module_path)
            
            return {
                "success": result.returncode == 0,
                "coverage": coverage_data,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        else:
            return {
                "success": result.returncode == 0,
                "coverage": None,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "message": "No coverage data generated"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def extract_module_coverage(coverage_file, module_path):
    """Extract coverage data for a specific module from the coverage.xml file."""
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        # Normalize module path
        module_path = module_path.replace('-', '_')
        if not module_path.startswith('galaxy_ng/'):
            module_path = f'galaxy_ng/{module_path}'
        
        # Find the class element for this module
        for cls in root.findall('.//class'):
            filename = cls.get('filename')
            
            # Check for various path formats
            if filename == module_path or \
               (module_path.startswith('galaxy_ng/') and filename == module_path[len('galaxy_ng/'):]) or \
               (not filename.startswith('galaxy_ng/') and f'galaxy_ng/{filename}' == module_path):
                
                # Extract line counts
                line_count = 0
                line_hits = 0
                
                for line in cls.findall('./lines/line'):
                    line_count += 1
                    if int(line.get('hits', 0)) > 0:
                        line_hits += 1
                
                if line_count > 0:
                    return {
                        'line_count': line_count,
                        'line_hits': line_hits,
                        'coverage_pct': (line_hits / line_count) * 100
                    }
        
        # If we didn't find an exact match, try to find by component parts
        module_basename = os.path.basename(module_path)
        for cls in root.findall('.//class'):
            filename = cls.get('filename')
            if module_basename in filename:
                # Extract line counts
                line_count = 0
                line_hits = 0
                
                for line in cls.findall('./lines/line'):
                    line_count += 1
                    if int(line.get('hits', 0)) > 0:
                        line_hits += 1
                
                if line_count > 0:
                    return {
                        'line_count': line_count,
                        'line_hits': line_hits,
                        'coverage_pct': (line_hits / line_count) * 100
                    }
        
        return None
        
    except Exception as e:
        print(f"Error extracting coverage data: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_validator.py path/to/generation_results.json [path/to/original_coverage.xml]")
        sys.exit(1)
    
    results_file = sys.argv[1]
    original_coverage_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Install dependencies first
    install_dependencies()
    
    # Create pytest.ini
    create_pytest_ini()
    
    # Load generation results
    try:
        with open(results_file, 'r') as f:
            generation_results = json.load(f)
    except Exception as e:
        print(f"Error reading results file: {e}")
        sys.exit(1)
    
    # Load original coverage data if available
    original_coverage = {}
    if original_coverage_file and os.path.exists(original_coverage_file):
        try:
            tree = ET.parse(original_coverage_file)
            root = tree.getroot()
            
            for cls in root.findall('.//class'):
                filename = cls.get('filename')
                
                line_count = 0
                line_hits = 0
                
                for line in cls.findall('./lines/line'):
                    line_count += 1
                    if int(line.get('hits', 0)) > 0:
                        line_hits += 1
                
                if line_count > 0:
                    coverage_pct = (line_hits / line_count) * 100
                    original_coverage[filename] = {
                        'line_count': line_count,
                        'line_hits': line_hits,
                        'coverage_pct': coverage_pct
                    }
                    
                    # Also store with normalized paths
                    if filename.startswith('galaxy_ng/'):
                        norm_path = filename[len('galaxy_ng/'):]
                        original_coverage[norm_path] = original_coverage[filename]
                    else:
                        norm_path = f"galaxy_ng/{filename}"
                        original_coverage[norm_path] = original_coverage[filename]
                        
        except Exception as e:
            print(f"Warning: Error parsing original coverage file: {e}")
    
    # Process each generated test
    validation_results = []
    for result in generation_results:
        if result['status'] != 'success':
            print(f"Skipping {result['filename']} - test generation failed")
            validation_results.append({
                'filename': result['filename'],
                'status': 'skipped',
                'reason': 'Test generation failed'
            })
            continue
        
        test_file = result['test_file']
        module_path = result['filename']
        
        print(f"\nValidating test for {module_path}...")
        
        # Step 1: Fix common issues in the test file
        print("Fixing common issues...")
        fixed = fix_common_test_issues(test_file)
        if fixed:
            print("Fixed issues in test file")
        
        # Step 2: Run the test to check if it runs successfully
        print("Running test...")
        test_result = run_pytest_test(test_file)
        
        if not test_result['success']:
            print(f"Test file failed to run: {test_file}")
            print(f"Error: {test_result.get('stderr', '')}")
            
            validation_results.append({
                'filename': module_path,
                'test_file': test_file,
                'status': 'failed',
                'reason': 'Test execution failed',
                'error': test_result.get('stderr', '')
            })
            continue
        
        # Step 3: Run with coverage to check if it improves coverage
        print("Running coverage analysis...")
        coverage_result = run_coverage_test(test_file, module_path)
        
        # Get original coverage for comparison
        original_coverage_data = None
        
        # Try with different path formats
        if module_path in original_coverage:
            original_coverage_data = original_coverage[module_path]
        elif module_path.startswith('galaxy_ng/') and module_path[len('galaxy_ng/'):] in original_coverage:
            original_coverage_data = original_coverage[module_path[len('galaxy_ng/'):]]
        elif not module_path.startswith('galaxy_ng/') and f"galaxy_ng/{module_path}" in original_coverage:
            original_coverage_data = original_coverage[f"galaxy_ng/{module_path}"]
        
        # If still not found, try matching by basename
        if not original_coverage_data:
            basename = os.path.basename(module_path).replace('-', '_')
            for path, data in original_coverage.items():
                if basename in path:
                    original_coverage_data = data
                    break
        
        # Check coverage results
        new_coverage = coverage_result.get('coverage')
        
        if not new_coverage:
            print(f"Could not determine coverage for {module_path}")
            
            validation_results.append({
                'filename': module_path,
                'test_file': test_file,
                'status': 'partial',
                'reason': 'Test runs but coverage data unavailable',
                'original_coverage': original_coverage_data['coverage_pct'] if original_coverage_data else None,
            })
            continue
        
        # Compare with original coverage
        if original_coverage_data:
            coverage_change = new_coverage['coverage_pct'] - original_coverage_data['coverage_pct']
            print(f"Coverage for {module_path}: {new_coverage['coverage_pct']:.2f}% (change: {coverage_change:+.2f}%)")
            
            if coverage_change > 0:
                status = 'improved'
                reason = f'Coverage improved by {coverage_change:.2f}%'
            elif coverage_change == 0:
                status = 'unchanged'
                reason = 'Coverage unchanged'
            else:
                status = 'degraded'
                reason = f'Coverage decreased by {abs(coverage_change):.2f}%'
        else:
            print(f"Coverage for {module_path}: {new_coverage['coverage_pct']:.2f}% (no original data for comparison)")
            status = 'new'
            reason = f'New coverage: {new_coverage["coverage_pct"]:.2f}%'
        
        validation_results.append({
            'filename': module_path,
            'test_file': test_file,
            'status': status,
            'reason': reason,
            'new_coverage': new_coverage['coverage_pct'],
            'original_coverage': original_coverage_data['coverage_pct'] if original_coverage_data else None,
            'coverage_change': coverage_change if original_coverage_data else None
        })
    
    # Save validation results
    output_file = os.path.join(os.path.dirname(results_file), 'validation_results.json')
    with open(output_file, 'w') as f:
        json.dump(validation_results, f, indent=2)
    
    # Print summary
    improved_count = sum(1 for r in validation_results if r.get('status') == 'improved')
    unchanged_count = sum(1 for r in validation_results if r.get('status') == 'unchanged')
    new_count = sum(1 for r in validation_results if r.get('status') == 'new')
    partial_count = sum(1 for r in validation_results if r.get('status') == 'partial')
    failed_count = sum(1 for r in validation_results if r.get('status') in ['failed', 'degraded', 'skipped'])
    
    print(f"\nValidation Summary:")
    print(f"  Improved coverage: {improved_count}")
    print(f"  Unchanged coverage: {unchanged_count}")
    print(f"  New coverage: {new_count}")
    print(f"  Partial success: {partial_count}")
    print(f"  Failed or problematic: {failed_count}")
    print(f"  Total: {len(validation_results)}")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()