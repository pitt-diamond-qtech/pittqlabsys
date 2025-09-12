#!/usr/bin/env python3
"""
Path Pattern Fixer Script

⚠️  WARNING: THIS SCRIPT IS UNTESTED AND POTENTIALLY DANGEROUS! ⚠️

This script attempts to automatically fix hardcoded path patterns in project files by 
replacing them with the robust get_project_root() function from src.core.helper_functions.

⚠️  IMPORTANT WARNINGS:
- This script is COMPLETELY UNTESTED
- It may BREAK WORKING CODE
- It may introduce import order issues
- It may create syntax errors
- Always backup your code before running
- Review all changes carefully before committing

Common patterns it attempts to fix:
- sys.path.insert(0, str(Path(__file__).parent / '..'))
- sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
- sys.path.insert(0, 'src')
- Adds missing get_project_root imports

Usage (AT YOUR OWN RISK):
    python examples/fix_path_patterns.py

RECOMMENDATION: Use this script as a reference only, and manually update files
one by one with careful testing.
"""

import os
import re
from pathlib import Path

def fix_file(file_path):
    """Fix hardcoded path patterns in a single file."""
    print(f"Processing: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Pattern 1: # Add project root to Python path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root))
        pattern1 = r"sys\.path\.insert\(0,\s*str\(Path\(__file__\)\.parent\s*/\s*['\"]\.\.['\"]\)\)"
        replacement1 = """# Add project root to Python path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root))"""
        
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
            changes_made.append("Fixed sys.path.insert pattern")
        
        # Pattern 2: # Add project root to Python path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root))
        pattern2 = r"sys\.path\.insert\(0,\s*str\(Path\(__file__\)\.parent\.parent\s*/\s*['\"]src['\"]\)\)"
        replacement2 = """# Add project root to Python path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root))"""
        
        if re.search(pattern2, content):
            content = re.sub(pattern2, replacement2, content)
            changes_made.append("Fixed sys.path.insert with parent.parent pattern")
        
        # Pattern 3: # Add project root to Python path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root)) (simple case)
        pattern3 = r"sys\.path\.insert\(0,\s*['\"]src['\"]\)"
        replacement3 = """# Add project root to Python path
from src.core.helper_functions import get_project_root
project_root = get_project_root()
sys.path.insert(0, str(project_root))"""
        
        if re.search(pattern3, content):
            content = re.sub(pattern3, replacement3, content)
            changes_made.append("Fixed simple sys.path.insert pattern")
        
        # Pattern 4: Path(__file__).parent / "relative_path" (for output directories, etc.)
        # This is more complex and needs to be handled carefully
        # We'll look for common patterns and suggest replacements
        
        # Pattern 5: Fix import order - ensure sys.path.insert comes before src imports
        if "from src.core.helper_functions import get_project_root" in content:
            # Check if the import is before sys.path.insert
            lines = content.split('\n')
            import_line_idx = None
            sys_path_line_idx = None
            
            for i, line in enumerate(lines):
                if "from src.core.helper_functions import get_project_root" in line:
                    import_line_idx = i
                if "sys.path.insert(0, str(project_root))" in line:
                    sys_path_line_idx = i
            
            # If import comes before sys.path.insert, we need to fix the order
            if import_line_idx is not None and sys_path_line_idx is not None and import_line_idx < sys_path_line_idx:
                # Move the import lines after sys.path.insert
                import_lines = []
                for i in range(import_line_idx, min(import_line_idx + 3, len(lines))):
                    if "from src.core.helper_functions import get_project_root" in lines[i] or "project_root = get_project_root()" in lines[i]:
                        import_lines.append(lines[i])
                        lines[i] = ""  # Remove from original position
                
                # Insert after sys.path.insert
                if sys_path_line_idx < len(lines):
                    lines.insert(sys_path_line_idx + 1, "")
                    for j, import_line in enumerate(import_lines):
                        lines.insert(sys_path_line_idx + 2 + j, import_line)
                
                content = '\n'.join(lines)
                changes_made.append("Fixed import order")
        
        # Pattern 6: Add import if not already present
        elif "from src.core.helper_functions import get_project_root" not in content:
            # Find the last import statement
            import_pattern = r"(import\s+[^\n]+\n)"
            imports = re.findall(import_pattern, content)
            if imports:
                last_import = imports[-1]
                # Insert after the last import
                content = content.replace(last_import, last_import + "\nfrom src.core.helper_functions import get_project_root\n")
                changes_made.append("Added get_project_root import")
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✅ Made changes: {', '.join(changes_made)}")
            return True
        else:
            print(f"  ⚪ No changes needed")
            return False
            
    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False

def test_fixes():
    """Test that the fixes work by running a few example files."""
    print("\n🧪 Testing fixes...")
    print("-" * 30)
    
    # Test files to check
    test_files = [
        "examples/awg520_example.py",
        "examples/confocal_scan_example.py", 
        "tests/test_device_config.py"
    ]
    
    project_root = Path(__file__).parent.parent
    
    for test_file in test_files:
        file_path = project_root / test_file
        if file_path.exists():
            try:
                # Try to import the file to see if it works
                import subprocess
                result = subprocess.run([
                    "python", "-c", 
                    f"import sys; sys.path.insert(0, '{project_root}'); exec(open('{file_path}').read())"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"✅ {test_file} - Import successful")
                else:
                    print(f"⚠️  {test_file} - Import failed: {result.stderr[:100]}...")
            except Exception as e:
                print(f"⚠️  {test_file} - Test error: {e}")
        else:
            print(f"⚠️  {test_file} - File not found")

def main():
    """Main function to process all files."""
    print("🔧 Fixing hardcoded path patterns in project files")
    print("=" * 60)
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Directories to process
    directories = [
        "examples",
        "tests", 
        "src/tools",
        "src/View",
        "src/Controller"
    ]
    
    # File extensions to process
    extensions = [".py"]
    
    total_files = 0
    files_changed = 0
    
    for directory in directories:
        dir_path = project_root / directory
        if not dir_path.exists():
            print(f"⚠️  Directory not found: {directory}")
            continue
            
        print(f"\n📁 Processing directory: {directory}")
        print("-" * 40)
        
        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in extensions:
                total_files += 1
                if fix_file(file_path):
                    files_changed += 1
    
    print(f"\n📊 Summary:")
    print(f"  Total files processed: {total_files}")
    print(f"  Files changed: {files_changed}")
    print(f"  Files unchanged: {total_files - files_changed}")
    
    if files_changed > 0:
        print(f"\n✅ Successfully updated {files_changed} files!")
        print("⚠️  Please review the changes and test the files to ensure they work correctly.")
        
        # Test a few files
        test_fixes()
    else:
        print("\n✅ No files needed updating!")

if __name__ == "__main__":
    main()
