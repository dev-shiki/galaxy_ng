#!/usr/bin/env python3
"""
This script analyzes a coverage report to identify modules with low coverage
that would be good candidates for AI-powered test generation.
Fixed to handle Galaxy NG specific paths correctly.
"""

import os
import sys
import xml.etree.ElementTree as ET
import json
from collections import defaultdict

def normalize_path(path):
    """
    Normalize path for coverage comparison by handling galaxy_ng prefix.
    """
    # Strip galaxy_ng/ prefix if present
    if path.startswith('galaxy_ng/'):
        normalized = path[len('galaxy_ng/'):]
    else:
        normalized = path
    
    return normalized

def parse_coverage_report(coverage_file):
    """Parse the coverage.xml file and extract module-level coverage data."""
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing coverage file: {e}")
        return None

    coverage_data = defaultdict(dict)
    
    # Get all classes in the coverage report
    all_classes = root.findall('.//class')
    print(f"Found {len(all_classes)} classes in coverage file")
    
    # Process each class (module) in the coverage report
    for cls in all_classes:
        filename = cls.get('filename')
        
        # Skip test files and migrations
        if '/tests/' in filename or '/migrations/' in filename:
            continue
            
        line_count = 0
        line_hits = 0
        
        # Count line hits
        for line in cls.findall('./lines/line'):
            line_count += 1
            if int(line.get('hits', 0)) > 0:
                line_hits += 1
        
        if line_count > 0:
            coverage_pct = (line_hits / line_count) * 100
            
            # Store data with original path
            coverage_data[filename] = {
                'line_count': line_count,
                'line_hits': line_hits,
                'coverage_pct': coverage_pct,
                'missing_lines': line_count - line_hits
            }
            
            # Also store with normalized path for better matching
            norm_path = normalize_path(filename)
            coverage_data[norm_path] = {
                'line_count': line_count,
                'line_hits': line_hits,
                'coverage_pct': coverage_pct,
                'missing_lines': line_count - line_hits,
                'original_path': filename  # Keep reference to original path
            }
    
    return coverage_data

def verify_file_exists(filename):
    """Check if file exists, considering possible prefixes."""
    possible_paths = [
        filename,
        f"galaxy_ng/{filename}",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    # File doesn't exist with any known prefixes
    return None

def identify_test_candidates(coverage_data, min_lines=10, max_coverage=70):
    """Identify modules that are good candidates for test generation."""
    candidates = []
    
    for filename, data in coverage_data.items():
        # Skip normalized duplicates that have an original_path
        if 'original_path' in data:
            continue
            
        # Check if the file actually exists in the repository
        actual_path = verify_file_exists(filename)
        if not actual_path:
            # Try checking normalized path if original doesn't exist
            norm_path = normalize_path(filename)
            actual_path = verify_file_exists(norm_path)
            if not actual_path:
                # Skip files that don't exist in the repository
                continue
            
        # We want modules with a reasonable number of lines but low coverage
        if (data['line_count'] >= min_lines and 
            data['coverage_pct'] <= max_coverage and
            data['missing_lines'] >= 5):
            
            candidates.append({
                'filename': filename,  # Keep original filename for coverage lookup
                'actual_path': actual_path,  # Add the verified path
                'coverage_pct': data['coverage_pct'],
                'missing_lines': data['missing_lines'],
                'priority_score': data['missing_lines'] * (100 - data['coverage_pct']) / 100
            })
    
    # Sort by priority score (higher score = better candidate)
    candidates.sort(key=lambda x: x['priority_score'], reverse=True)
    
    return candidates

def main():
    if len(sys.argv) < 2:
        print("Usage: python coverage_analyzer.py path/to/coverage.xml [output_file.json]")
        sys.exit(1)
    
    coverage_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "test_candidates.json"
    
    if not os.path.exists(coverage_file):
        print(f"Coverage file {coverage_file} not found")
        sys.exit(1)
    
    coverage_data = parse_coverage_report(coverage_file)
    if not coverage_data:
        print("Failed to parse coverage data")
        sys.exit(1)
    
    candidates = identify_test_candidates(coverage_data)
    
    # Skip candidates that don't actually exist in filesystem
    valid_candidates = [c for c in candidates if c['actual_path']]
    
    if not valid_candidates:
        print("WARNING: No valid candidates found. Are the paths in the coverage file correct?")
        # Print some sample paths from coverage data for debugging
        sample_paths = list(coverage_data.keys())[:10]
        print(f"Sample paths from coverage file: {sample_paths}")
    
    # Limit to top candidates to keep the process manageable
    top_candidates = valid_candidates[:10]
    
    print(f"Identified {len(top_candidates)} priority modules for test generation")
    for i, candidate in enumerate(top_candidates, 1):
        print(f"{i}. {candidate['actual_path']} - {candidate['coverage_pct']:.2f}% coverage, {candidate['missing_lines']} missing lines")
    
    # Write candidates to JSON file
    with open(output_file, 'w') as f:
        json.dump(top_candidates, f, indent=2)
    
    print(f"Candidate list written to {output_file}")

if __name__ == "__main__":
    main()