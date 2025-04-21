"""
Veramon Reunited Codebase Analyzer
Created: April 21, 2025

This script analyzes the entire Veramon Reunited codebase to identify:
1. Redundant files
2. Temporary or backup files
3. Orphaned data files
4. Unused imports
5. Commented-out code blocks
6. Empty files and directories
"""

import os
import re
import sys
import json
from pathlib import Path
import importlib.util
import ast
from collections import defaultdict

class CodebaseAnalyzer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results = {
            "backup_files": [],
            "temp_files": [],
            "data_part_files": [],
            "redundant_files": [],
            "empty_files": [],
            "empty_dirs": [],
            "unused_imports": {},
            "commented_code": {}
        }
        self.extensions = {
            "python": [".py"],
            "data": [".json", ".yaml", ".yml", ".csv"],
            "docs": [".md", ".txt", ".rst"],
            "web": [".html", ".css", ".js"]
        }
        self.all_modules = set()
        self.used_modules = set()

    def analyze(self):
        """Run the full analysis on the codebase"""
        print(f"=== Analyzing Veramon Reunited Codebase ===")
        print(f"Project root: {self.project_root}")
        
        # Identify all relevant files
        self._scan_files()
        
        # Analyze Python code
        self._analyze_python_files()
        
        # Analyze data files
        self._analyze_data_files()
        
        # Print results
        self._print_results()
        
        return self.results

    def _scan_files(self):
        """Scan all files and identify potential issues"""
        print("\nScanning files...")
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip .git and venv directories
            dirs[:] = [d for d in dirs if d not in ['.git', 'venv', 'env', '.venv', '__pycache__']]
            
            # Check if directory is empty
            if not dirs and not files:
                rel_path = os.path.relpath(root, self.project_root)
                self.results["empty_dirs"].append(rel_path)
            
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.project_root)
                
                # Check for empty files
                if os.path.getsize(full_path) == 0:
                    self.results["empty_files"].append(rel_path)
                
                # Check for backup files
                if file.endswith(('.bak', '~', '.old', '.backup')) or '.bak.' in file:
                    self.results["backup_files"].append(rel_path)
                    continue
                
                # Check for temporary files
                if file.startswith('temp_') or file.startswith('tmp_') or file.endswith('.tmp'):
                    self.results["temp_files"].append(rel_path)
                    continue
                
                # Check for veramon data part files (these should now be consolidated)
                if file.startswith('veramon_data_part') and file.endswith('.json'):
                    self.results["data_part_files"].append(rel_path)
                    continue
                
                # Build a list of Python modules
                if file.endswith('.py'):
                    module_path = rel_path.replace(os.sep, '.').replace('.py', '')
                    self.all_modules.add(module_path)

    def _analyze_python_files(self):
        """Analyze Python files for issues"""
        print("\nAnalyzing Python files...")
        
        for root, _, files in os.walk(self.project_root):
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.project_root)
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for commented out code
                    commented_lines = self._find_commented_code(content)
                    if commented_lines:
                        self.results["commented_code"][rel_path] = commented_lines
                    
                    # Check for unused imports
                    unused = self._find_unused_imports(content, full_path)
                    if unused:
                        self.results["unused_imports"][rel_path] = unused
                        
                except Exception as e:
                    print(f"Error analyzing {rel_path}: {e}")

    def _find_commented_code(self, content):
        """Find blocks of commented code"""
        lines = content.split('\n')
        commented_blocks = []
        current_block = []
        in_block = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines and docstrings
            if not stripped or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            
            if stripped.startswith('#'):
                # Ignore comment lines that are clearly not code
                comment_text = stripped[1:].strip()
                if (len(comment_text) > 0 and 
                    not comment_text[0].isalpha() and 
                    not comment_text[0] in ['{', '[', '(', '"', "'"]):
                    continue
                    
                # Check if this looks like commented out code
                code_indicators = ['def ', 'class ', 'import ', 'from ', ' = ', 'if ', 'for ', 'while ']
                is_code = any(indicator in comment_text for indicator in code_indicators)
                
                if is_code:
                    if not in_block:
                        in_block = True
                        current_block = []
                    current_block.append((i+1, line))
            else:
                if in_block and len(current_block) > 3:  # Only count blocks with more than 3 lines
                    commented_blocks.append(current_block)
                in_block = False
                current_block = []
        
        # Check for any final block
        if in_block and len(current_block) > 3:
            commented_blocks.append(current_block)
            
        return commented_blocks

    def _find_unused_imports(self, content, file_path):
        """Find unused imports in a Python file"""
        try:
            tree = ast.parse(content)
            
            # Find all imports
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.add(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module
                    for name in node.names:
                        if name.name != '*':
                            imports.add(f"{module}.{name.name}" if module else name.name)
            
            # Find all used names
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                    # Handle attributes like module.function
                    names = []
                    current = node
                    while isinstance(current, ast.Attribute):
                        names.append(current.attr)
                        current = current.value
                    if isinstance(current, ast.Name):
                        names.append(current.id)
                        used_names.add('.'.join(reversed(names)))
            
            # Determine unused imports
            unused = []
            for imp in imports:
                parts = imp.split('.')
                if parts[0] not in used_names and imp not in used_names:
                    # Make sure it's not a module-level import used elsewhere
                    is_used = False
                    for used in used_names:
                        if used.startswith(f"{parts[0]}."):
                            is_used = True
                            break
                    if not is_used:
                        unused.append(imp)
            
            return unused
        except SyntaxError:
            return []

    def _analyze_data_files(self):
        """Analyze data files for issues"""
        print("\nAnalyzing data files...")
        
        # Check for unused data files
        data_dir = self.project_root / 'src' / 'data'
        if not data_dir.exists():
            return
            
        # Get all the json files in the data directory
        json_files = list(data_dir.glob('*.json'))
        
        # Special checks for veramon data files
        data_files = {f.name: f for f in json_files}
        
        if 'veramon_database.json' in data_files and 'veramon_data.json' in data_files:
            # Check if both files contain the same Veramon
            try:
                with open(data_files['veramon_database.json'], 'r', encoding='utf-8') as f:
                    database = json.load(f)
                with open(data_files['veramon_data.json'], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                duplicates = set(database.keys()) & set(data.keys())
                if duplicates:
                    rel_path = os.path.relpath(data_files['veramon_data.json'], self.project_root)
                    self.results["redundant_files"].append({
                        "file": rel_path,
                        "reason": f"Contains {len(duplicates)} duplicate Veramon already in veramon_database.json"
                    })
            except Exception as e:
                print(f"Error comparing data files: {e}")

    def _print_results(self):
        """Print analysis results"""
        print("\n=== Analysis Results ===")
        
        total_issues = sum(len(items) for items in self.results.values() if isinstance(items, list))
        total_issues += sum(len(items) for items in self.results.values() if isinstance(items, dict))
        
        print(f"Found {total_issues} potential issues:")
        
        if self.results["backup_files"]:
            print(f"\n{len(self.results['backup_files'])} backup files:")
            for file in self.results["backup_files"][:5]:
                print(f"  - {file}")
            if len(self.results["backup_files"]) > 5:
                print(f"  ... and {len(self.results['backup_files']) - 5} more")
                
        if self.results["temp_files"]:
            print(f"\n{len(self.results['temp_files'])} temporary files:")
            for file in self.results["temp_files"][:5]:
                print(f"  - {file}")
            if len(self.results["temp_files"]) > 5:
                print(f"  ... and {len(self.results['temp_files']) - 5} more")
                
        if self.results["data_part_files"]:
            print(f"\n{len(self.results['data_part_files'])} Veramon data part files (should be consolidated):")
            for file in self.results["data_part_files"]:
                print(f"  - {file}")
                
        if self.results["redundant_files"]:
            print(f"\n{len(self.results['redundant_files'])} redundant files:")
            for item in self.results["redundant_files"]:
                print(f"  - {item['file']}: {item['reason']}")
                
        if self.results["empty_files"]:
            print(f"\n{len(self.results['empty_files'])} empty files:")
            for file in self.results["empty_files"][:5]:
                print(f"  - {file}")
            if len(self.results["empty_files"]) > 5:
                print(f"  ... and {len(self.results['empty_files']) - 5} more")
                
        if self.results["empty_dirs"]:
            print(f"\n{len(self.results['empty_dirs'])} empty directories:")
            for dir in self.results["empty_dirs"][:5]:
                print(f"  - {dir}")
            if len(self.results["empty_dirs"]) > 5:
                print(f"  ... and {len(self.results['empty_dirs']) - 5} more")
                
        if self.results["unused_imports"]:
            print(f"\n{len(self.results['unused_imports'])} files with unused imports:")
            for file, imports in list(self.results["unused_imports"].items())[:5]:
                print(f"  - {file}: {', '.join(imports[:3])}" + 
                      (f" and {len(imports) - 3} more" if len(imports) > 3 else ""))
            if len(self.results["unused_imports"]) > 5:
                print(f"  ... and {len(self.results['unused_imports']) - 5} more files")
                
        if self.results["commented_code"]:
            print(f"\n{len(self.results['commented_code'])} files with commented out code blocks:")
            for file, blocks in list(self.results["commented_code"].items())[:5]:
                print(f"  - {file}: {len(blocks)} block(s), first at line {blocks[0][0][0]}")
            if len(self.results["commented_code"]) > 5:
                print(f"  ... and {len(self.results['commented_code']) - 5} more files")
                
        print("\n=== Cleanup Recommendations ===")
        
        if self.results["data_part_files"]:
            print("1. Remove Veramon data part files as they've been consolidated into veramon_database.json")
            
        if self.results["backup_files"] or self.results["temp_files"]:
            print("2. Clean up backup and temporary files")
            
        if self.results["empty_files"] or self.results["empty_dirs"]:
            print("3. Consider removing empty files and directories")
            
        if self.results["redundant_files"]:
            print("4. Remove redundant data files")
        
        print("\nUse src/tools/cleanup_redundant_files.py to automatically clean up these issues")

def create_cleanup_script(results, project_root):
    """Create a script to clean up redundant files"""
    print("\nCreating cleanup script...")
    
    script_content = """\"\"\"
Veramon Reunited Redundant Files Cleanup
Created: April 21, 2025

This script cleans up redundant files identified by the codebase analyzer.
\"\"\"

import os
import sys
import shutil
from pathlib import Path

def cleanup_redundant_files():
    \"\"\"Clean up redundant files in the Veramon Reunited codebase\"\"\"
    print("=== Veramon Reunited Redundant Files Cleanup ===")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    backup_dir = project_root / "redundant_files_backup"
    backup_dir.mkdir(exist_ok=True)
    
    files_to_remove = [
"""
    
    # Add the files to remove
    files_to_backup = []
    
    # Add data part files
    for file in results["data_part_files"]:
        files_to_backup.append(f'        # Data part file (consolidated into veramon_database.json)\n        "{file}",')
    
    # Add redundant files
    for item in results["redundant_files"]:
        files_to_backup.append(f'        # {item["reason"]}\n        "{item["file"]}",')
    
    # Add backup files
    for file in results["backup_files"]:
        files_to_backup.append(f'        # Backup file\n        "{file}",')
    
    # Add temp files
    for file in results["temp_files"]:
        files_to_backup.append(f'        # Temporary file\n        "{file}",')
    
    script_content += "\n".join(files_to_backup)
    
    script_content += """
    ]
    
    successful = 0
    failed = 0
    
    # First backup all files
    print("\\nBacking up files...")
    for file_path in files_to_remove:
        full_path = project_root / file_path
        if not full_path.exists():
            print(f"  - {file_path}: SKIP (not found)")
            continue
            
        try:
            # Create parent directories in backup folder
            backup_path = backup_dir / file_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file to backup
            shutil.copy2(full_path, backup_path)
            print(f"  - {file_path}: Backed up")
        except Exception as e:
            print(f"  - {file_path}: ERROR backing up - {e}")
            failed += 1
    
    # Ask for confirmation before deleting
    print("\\nReady to delete files. All files have been backed up to:")
    print(f"  {backup_dir}")
    
    confirm = input("\\nProceed with deletion? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted. No files were deleted.")
        return
    
    # Delete files
    print("\\nDeleting files...")
    for file_path in files_to_remove:
        full_path = project_root / file_path
        if not full_path.exists():
            continue
            
        try:
            # Delete file
            os.remove(full_path)
            print(f"  - {file_path}: Deleted")
            successful += 1
        except Exception as e:
            print(f"  - {file_path}: ERROR deleting - {e}")
            failed += 1
    
    # Cleanup empty directories
    empty_dirs = [
"""
    
    # Add empty directories
    for dir in results["empty_dirs"]:
        script_content += f'        "{dir}",\n'
    
    script_content += """
    ]
    
    # Add directories that might be emptied by file removal
    potentially_empty = set()
    for file_path in files_to_remove:
        parent = os.path.dirname(file_path)
        while parent:
            potentially_empty.add(parent)
            parent = os.path.dirname(parent)
    
    print("\\nCleaning up empty directories...")
    for dir_path in empty_dirs + list(potentially_empty):
        full_path = project_root / dir_path
        if not full_path.exists() or not os.path.isdir(full_path):
            continue
            
        # Check if directory is empty
        if not os.listdir(full_path):
            try:
                os.rmdir(full_path)
                print(f"  - {dir_path}: Removed empty directory")
                successful += 1
            except Exception as e:
                print(f"  - {dir_path}: ERROR removing - {e}")
                failed += 1
    
    print("\\n=== Cleanup Summary ===")
    print(f"Successfully processed {successful} items")
    if failed > 0:
        print(f"Failed to process {failed} items")
    print(f"All files were backed up to: {backup_dir}")

if __name__ == "__main__":
    cleanup_redundant_files()
    sys.exit(0)
"""
    
    # Write the script
    script_path = os.path.join(project_root, 'src', 'tools', 'cleanup_redundant_files.py')
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
        
    print(f"Created cleanup script at {script_path}")
    return script_path

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    analyzer = CodebaseAnalyzer(project_root)
    results = analyzer.analyze()
    
    # Create cleanup script
    if any(len(items) > 0 for items in results.values()):
        cleanup_script = create_cleanup_script(results, project_root)
        print(f"\nRun the cleanup script to remove redundant files: python {cleanup_script}")
    
    sys.exit(0)
