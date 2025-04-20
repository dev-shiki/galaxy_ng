import os
import sys
import ast
import re

def check_file(filepath):
    print(f"Checking {filepath}...")
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Check for proper Django setup
        if "django.setup()" not in content:
            print(f"WARNING: Django setup missing in {filepath}")
        
        # Check for factory imports
        if re.search(r'from galaxy_ng\.[^\s]+\s+import\s+factories', content):
            print(f"WARNING: Direct factory import in {filepath}")
        
        # Validate syntax
        try:
            ast.parse(content)
            print(f"✅ {filepath} is syntactically valid")
            return True
        except SyntaxError as e:
            print(f"❌ {filepath} has syntax error: {e}")
            return False
    except Exception as e:
        print(f"Error checking {filepath}: {e}")
        return False

# Check all test files in the directory
test_dir = "galaxy_ng/tests/unit/ai_generated"
valid_count = 0
error_count = 0

if os.path.exists(test_dir):
    for file in os.listdir(test_dir):
        if file.endswith(".py") and file != "__init__.py":
            file_path = os.path.join(test_dir, file)
            if check_file(file_path):
                valid_count += 1
            else:
                error_count += 1
    
    print(f"\nValidation results: {valid_count} valid, {error_count} with errors")
    sys.exit(1 if error_count > 0 else 0)
else:
    print(f"Test directory {test_dir} not found")
    sys.exit(1)
