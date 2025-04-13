#!/usr/bin/env python3
"""
This script validates generated test files by running them with tox
and checking if they improve coverage. Fixed to handle path discrepancies.
"""

import os
import sys
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

def normalize_path(path):
    """
    Normalize path for coverage comparison by handling galaxy_ng prefix.
    This addresses the discrepancy between paths in coverage.xml and actual files.
    """
    # Strip galaxy_ng/ prefix if present
    if path.startswith('galaxy_ng/'):
        normalized = path[len('galaxy_ng/'):]
    else:
        normalized = path
    
    return normalized

def get_all_possible_paths(filename):
    """
    Get all possible variations of a path to handle discrepancies.
    """
    paths = [
        filename,
        f"galaxy_ng/{filename}",
    ]
    
    # Handle path without file extension (for __init__.py files)
    if filename.endswith('__init__.py'):
        base_dir = os.path.dirname(filename)
        paths.append(base_dir)
        paths.append(f"galaxy_ng/{base_dir}")
    
    return paths

def run_tox_test(test_file, env="py311"):
    """Run a specific test file using tox."""
    try:
        cmd = [
            "tox",
            "-e", env,
            "--",
            test_file,
            "-v"
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
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

def run_tox_coverage(test_file, module_path, env="py311"):
    """Run coverage analysis for a specific test file using tox."""
    with tempfile.TemporaryDirectory() as tmpdir:
        coverage_file = os.path.join(tmpdir, "coverage.xml")
        
        # Try to determine the correct module path to measure coverage for
        module_dir = os.path.dirname(module_path)
        if module_dir.startswith('galaxy_ng/'):
            cov_module = module_dir
        else:
            cov_module = f"galaxy_ng/{module_dir}"
        
        cmd = [
            "tox",
            "-e", env,
            "--",
            test_file,
            f"--cov={cov_module}",
            f"--cov-report=xml:{coverage_file}",
            "-v"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            coverage_data = None
            if os.path.exists(coverage_file):
                # First try direct path
                coverage_data = get_module_coverage(coverage_file, module_path)
                
                # If that fails, try with different path variations
                if not coverage_data:
                    for possible_path in get_all_possible_paths(module_path):
                        coverage_data = get_module_coverage(coverage_file, possible_path)
                        if coverage_data:
                            print(f"Found coverage data using path: {possible_path}")
                            break
                
                # If still no data, try looking through all classes in the coverage file
                if not coverage_data:
                    coverage_data = find_matching_coverage(coverage_file, module_path)
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "coverage": coverage_data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

def get_module_coverage(coverage_file, module_path):
    """Extract coverage for a specific module from coverage.xml."""
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        for cls in root.findall('.//class'):
            filename = cls.get('filename')
            if filename == module_path:
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
        print(f"Error parsing coverage file: {e}")
        return None

def find_matching_coverage(coverage_file, module_path):
    """
    Find coverage data by looking for a path that ends with the module path.
    This handles cases where the full path in coverage.xml is different.
    """
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        # Normalize the target path
        norm_target = normalize_path(module_path)
        
        # Debug: print all paths in coverage file
        all_paths = []
        for cls in root.findall('.//class'):
            filename = cls.get('filename')
            all_paths.append(filename)
        
        print(f"Searching for {norm_target} among {len(all_paths)} paths in coverage file")
        if all_paths:
            print(f"Sample paths: {all_paths[:5]}")
        
        # Find class that matches our path (end of path should match)
        for cls in root.findall('.//class'):
            filename = cls.get('filename')
            norm_filename = normalize_path(filename)
            
            # Check if the normalized path ends with our target
            if norm_filename.endswith(norm_target) or norm_target.endswith(norm_filename):
                print(f"Found matching path: {filename}")
                
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
        print(f"Error parsing coverage file: {e}")
        return None

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
        ]
        
        # Apply fixes
        modified_content = content
        for pattern, replacement in fixes:
            # Only apply if pattern not already in content
            if pattern not in modified_content:
                modified_content = replacement + modified_content
        
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
    original_coverage_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        with open(results_file, 'r') as f:
            generation_results = json.load(f)
    except Exception as e:
        print(f"Error reading results file: {e}")
        sys.exit(1)
    
    # Dictionary to hold original coverage data for comparison
    original_coverage = {}
    if original_coverage_file and os.path.exists(original_coverage_file):
        try:
            tree = ET.parse(original_coverage_file)
            root = tree.getroot()
            
            all_classes = root.findall('.//class')
            print(f"Found {len(all_classes)} classes in original coverage file")
            
            for cls in all_classes:
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
                    
                    # Also store normalized path versions
                    norm_filename = normalize_path(filename)
                    original_coverage[norm_filename] = {
                        'line_count': line_count,
                        'line_hits': line_hits,
                        'coverage_pct': coverage_pct
                    }
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
        print("Applying common fixes...")
        fixed = fix_common_issues(test_file, module_path)
        if fixed:
            print("Applied fixes to test file")
        
        # Step 2: Run pytest to check if the test runs successfully
        print("Running test with tox...")
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
            continue
        
        # Step 3: Run with coverage to see if it improves coverage
        print("Running with coverage analysis...")
        coverage_result = run_tox_coverage(test_file, module_path)
        
        # Get original coverage for comparison
        original_coverage_data = None
        
        # Try different path variations for looking up original coverage
        for possible_path in get_all_possible_paths(module_path):
            if possible_path in original_coverage:
                original_coverage_data = original_coverage[possible_path]
                print(f"Found original coverage data using path: {possible_path}")
                break
        
        # Check if coverage improved
        new_coverage = coverage_result.get('coverage')
        
        if not new_coverage:
            print(f"Could not determine coverage for {module_path}")
            validation_results.append({
                'filename': module_path,
                'test_file': test_file,
                'status': 'partial',
                'reason': 'Test runs but coverage data unavailable'
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
    failed_count = sum(1 for r in validation_results if r.get('status') in ['failed', 'partial', 'degraded', 'skipped'])
    
    print(f"\nValidation Summary:")
    print(f"  Improved coverage: {improved_count}")
    print(f"  Unchanged coverage: {unchanged_count}")
    print(f"  New coverage: {new_count}")
    print(f"  Failed or problematic: {failed_count}")
    print(f"  Total: {len(validation_results)}")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()