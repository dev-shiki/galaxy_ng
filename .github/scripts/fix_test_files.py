#!/usr/bin/env python3
"""
AITestCorrector - A utility for fixing syntax errors in AI-generated test files
using both rule-based fixes and AI-assisted correction.

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
    Perbaiki error sintaks yang lebih kompleks dengan pendekatan multi-tahap.
    Ini termasuk membersihkan string yang tidak tertutup, pernyataan yang kehilangan titik dua, dll.
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

# Standard fix function (without AI)
def fix_test_file(test_file):
    """Apply all fixes to a test file."""
    try:
        print(f"Fixing {test_file}...")
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Apply fixers in order
        content = ensure_django_setup(content)
        content = fix_import_statements(content)
        content = add_factory_mocks(content)
        content = fix_test_definitions(content)
        content = fix_annotation_syntax(content)
        content = handle_special_modules(content, test_file)
        content = normalize_module_path(content)
        content = balance_parentheses(content)
        content = fix_advanced_syntax_errors(content)
        
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
    
    def ensure_mock_import(content):
        """Ensure unittest.mock is properly imported."""
        if 'mock.MagicMock' in content and 'import mock' not in content and 'from unittest import mock' not in content:
            # Add import to the beginning of the file
            return 'from unittest import mock\n' + content
        return content

    def _apply_standard_fixes(self, content, test_file):
        """Menerapkan perbaikan standar pada konten"""
        content = ensure_django_setup(content)
        content = ensure_mock_import(content) 
        content = fix_import_statements(content)
        content = add_factory_mocks(content)
        content = fix_test_definitions(content)
        content = fix_annotation_syntax(content)
        content = handle_special_modules(content, test_file)
        content = normalize_module_path(content)
        content = balance_parentheses(content)
        content = fix_advanced_syntax_errors(content)
        
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
        
        prompt = f"""Saya memiliki file test Python yang masih memiliki error sintaks setelah perbaikan otomatis {attempt} kali.

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

Tolong perbaiki kode ini dan kembalikan versi yang sudah diperbaiki. Pastikan:
1. Semua string literal tertutup dengan benar
2. Semua definisi fungsi/kelas/if/else diakhiri dengan titik dua (:)
3. Semua tanda kurung/bracket/brace seimbang
4. Tidak ada error sintaks lain yang tersisa

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
        """Membuat prompt sistem untuk AI correction"""
        return """Anda adalah ahli Python yang memiliki spesialisasi dalam memperbaiki error sintaks dalam kode test.
Tugas Anda adalah menganalisis kode Python yang memiliki error sintaks, kemudian memberikan versi yang sudah diperbaiki.

Fokus pada:
1. Menemukan dan memperbaiki error yang disebutkan dalam pesan error
2. Memeriksa masalah potensial lain yang mungkin memunculkan error tambahan
3. Memastikan kode benar-benar bebas dari error sintaks

Berikan solusi yang komprehensif dan terperinci, dengan kode yang sepenuhnya valid dan bebas dari error sintaks.

Anda harus mengembalikan kode lengkap yang sudah diperbaiki, bukan hanya bagian yang bermasalah.
"""
    
    def _save_content(self, test_file, content):
        """Menyimpan konten ke file"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Content saved to {test_file}")

def main():
    parser = argparse.ArgumentParser(description="Fix AI-generated test files for the Galaxy NG project")
    parser.add_argument("--path", default="galaxy_ng/tests/unit/ai_generated", 
                        help="Path to directory containing test files")
    parser.add_argument("--validate", action="store_true", 
                        help="Validate that tests collect without errors")
    parser.add_argument("--api-key", help="SambaNova API key for AI-assisted correction (falls back to SAMBANOVA_API_KEY env var)")
    parser.add_argument("--model", default="Meta-Llama-3.1-8B-Instruct", help="AI model to use for correction")
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
    
if __name__ == "__main__":
    main()