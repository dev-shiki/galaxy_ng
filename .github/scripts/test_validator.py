#!/usr/bin/env python3
"""
Simplified test validator that just runs the tests without trying to measure coverage.
This ensures the tests at least run correctly.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def run_tox_test(test_file, env="py311"):
    """Run a specific test file using tox."""
    try:
        cmd = [
            "python", "-m", "pytest",
            test_file,
            "-v"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Print test output for debugging
        print(f"Test stdout: {result.stdout[:500]}...")
        if result.stderr:
            print(f"Test stderr: {result.stderr[:500]}...")
            
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

def fix_common_issues(test_file, module_path):
    """Fix common issues in generated test files."""
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # List of common fixes to apply
        fixes = [
            # Fix missing or incorrect imports
            (r'import pytest\n', 'import pytest\nimport os\nimport sys\n'),
            
            # Fix django settings import if needed
            (r'from django.conf import settings', 'os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")\nfrom django.conf import settings'),
            
            # Add module base path if needed
            (r'import sys\n', 'import sys\n\n# Add project root to path if needed\nproject_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))\nif project_root not in sys.path:\n    sys.path.insert(0, project_root)\n'),
            
            # Add mock for any problematic imports
            (r'import pulp_smash', 'try:\n    import pulp_smash\nexcept ImportError:\n    pulp_smash = type("MockPulpSmash", (), {"config": type("MockConfig", (), {"get": lambda *args, **kwargs: None})})\n'),
        ]
        
        # Apply fixes
        modified_content = content
        for pattern, replacement in fixes:
            # Only apply if pattern not already in content
            if pattern in modified_content:
                modified_content = modified_content.replace(pattern, replacement)
        
        # Add global fixes at the top
        header = """
import os
import sys
import pytest
from unittest import mock

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")

# Mock problematic modules
sys.modules["pulp_smash"] = mock.MagicMock()
"""
        
        # Add the header if not already present (check for key elements)
        if "os.environ.setdefault" not in modified_content:
            modified_content = header + modified_content
        
        # Write back if changed
        if modified_content != content:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            return True
        
        return False
    
    except Exception as e:
        print(f"Error fixing test file: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_validator.py path/to/generation_results.json [path/to/original_coverage.xml]")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    try:
        with open(results_file, 'r') as f:
            generation_results = json.load(f)
    except Exception as e:
        print(f"Error reading results file: {e}")
        sys.exit(1)
    
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
        print("Applying common fixes...")
        fixed = fix_common_issues(test_file, module_path)
        if fixed:
            print("Applied fixes to test file")
        
        # Step 2: Run pytest to check if the test runs
        print("Running test...")
        pytest_result = run_tox_test(test_file)
        
        if not pytest_result['success']:
            print(f"Test file failed to run: {test_file}")
            print(f"Error: {pytest_result.get('stderr', '')}")
            
            validation_results.append({
                'filename': module_path,
                'test_file': test_file,
                'status': 'failed',
                'reason': 'Test execution failed',
                'error': pytest_result.get('stderr', '')
            })
        else:
            print(f"Test executed successfully: {test_file}")
            validation_results.append({
                'filename': module_path,
                'test_file': test_file,
                'status': 'success',
                'reason': 'Test runs successfully'
            })
    
    # Save validation results
    output_file = os.path.join(os.path.dirname(results_file), 'validation_results.json')
    with open(output_file, 'w') as f:
        json.dump(validation_results, f, indent=2)
    
    # Print summary
    success_count = sum(1 for r in validation_results if r.get('status') == 'success')
    failed_count = sum(1 for r in validation_results if r.get('status') in ['failed', 'partial', 'skipped'])
    
    print(f"\nValidation Summary:")
    print(f"  Successful tests: {success_count}")
    print(f"  Failed tests: {failed_count}")
    print(f"  Total: {len(validation_results)}")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()