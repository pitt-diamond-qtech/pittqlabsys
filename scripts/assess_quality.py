#!/usr/bin/env python3
"""
Quality Assessment Script

This script helps assess the quality of code, documentation, and commits
in the PittQLabSys project. It provides automated checks and scoring
to help with code review.

Usage:
    python scripts/assess_quality.py [--path PATH] [--commits N]
"""

import os
import sys
import subprocess
import ast
import argparse
from pathlib import Path
from typing import List, Dict, Any

def check_commit_messages(num_commits: int = 10) -> Dict[str, Any]:
    """Check quality of recent commit messages."""
    try:
        result = subprocess.run(
            ['git', 'log', '--oneline', f'-{num_commits}'],
            capture_output=True, text=True, check=True
        )
        commits = result.stdout.strip().split('\n')
        
        scores = {
            'total_commits': len(commits),
            'good_format': 0,
            'has_setup_name': 0,
            'descriptive': 0,
            'mentions_testing': 0,
            'issues': []
        }
        
        for commit in commits:
            if not commit:
                continue
                
            # Check format: [setup-name] Description
            if '[' in commit and ']' in commit:
                scores['good_format'] += 1
            else:
                scores['issues'].append(f"Missing format: {commit}")
            
            # Check for setup name
            if '[' in commit and ']' in commit:
                scores['has_setup_name'] += 1
            else:
                scores['issues'].append(f"Missing setup name: {commit}")
            
            # Check if descriptive (more than 10 characters after setup name)
            if ']' in commit and len(commit.split(']', 1)[1].strip()) > 10:
                scores['descriptive'] += 1
            else:
                scores['issues'].append(f"Not descriptive enough: {commit}")
            
            # Check if mentions testing
            if any(word in commit.lower() for word in ['test', 'mock', 'hardware']):
                scores['mentions_testing'] += 1
        
        return scores
    except subprocess.CalledProcessError as e:
        return {'error': f"Failed to get commit history: {e}"}

def check_docstring_quality(file_path: str) -> Dict[str, Any]:
    """Check docstring quality in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        scores = {
            'total_functions': 0,
            'functions_with_docstrings': 0,
            'total_classes': 0,
            'classes_with_docstrings': 0,
            'issues': []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                scores['total_functions'] += 1
                if ast.get_docstring(node):
                    scores['functions_with_docstrings'] += 1
                    # Check docstring quality
                    docstring = ast.get_docstring(node)
                    if len(docstring) < 20:
                        scores['issues'].append(f"Short docstring in {node.name}")
                    if 'Args:' not in docstring and 'Returns:' not in docstring:
                        scores['issues'].append(f"Missing Args/Returns in {node.name}")
                else:
                    scores['issues'].append(f"Missing docstring in {node.name}")
            
            elif isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
                scores['total_classes'] += 1
                if ast.get_docstring(node):
                    scores['classes_with_docstrings'] += 1
                    docstring = ast.get_docstring(node)
                    if len(docstring) < 50:
                        scores['issues'].append(f"Short class docstring in {node.name}")
                else:
                    scores['issues'].append(f"Missing docstring in {node.name}")
        
        return scores
    except Exception as e:
        return {'error': f"Failed to parse {file_path}: {e}"}

def check_code_quality(file_path: str) -> Dict[str, Any]:
    """Check basic code quality metrics."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        scores = {
            'total_lines': len(lines),
            'comment_lines': 0,
            'docstring_lines': 0,
            'long_lines': 0,
            'issues': []
        }
        
        in_docstring = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Count comment lines
            if stripped.startswith('#'):
                scores['comment_lines'] += 1
            
            # Count docstring lines
            if '"""' in line or "'''" in line:
                in_docstring = not in_docstring
                if in_docstring:
                    scores['docstring_lines'] += 1
            
            # Check for long lines
            if len(line) > 88:
                scores['long_lines'] += 1
                scores['issues'].append(f"Line {i} too long: {len(line)} characters")
            
            # Check for common issues
            if 'TODO' in line or 'FIXME' in line:
                scores['issues'].append(f"TODO/FIXME on line {i}: {stripped}")
            
            if 'print(' in line and '#' not in line:
                scores['issues'].append(f"Debug print on line {i}: {stripped}")
        
        return scores
    except Exception as e:
        return {'error': f"Failed to read {file_path}: {e}"}

def assess_directory(path: str) -> Dict[str, Any]:
    """Assess quality of entire directory."""
    results = {
        'commit_quality': check_commit_messages(),
        'files_analyzed': 0,
        'total_issues': 0,
        'file_results': {}
    }
    
    for root, dirs, files in os.walk(path):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                results['files_analyzed'] += 1
                
                # Check docstring quality
                docstring_results = check_docstring_quality(file_path)
                if 'error' not in docstring_results:
                    results['total_issues'] += len(docstring_results.get('issues', []))
                
                # Check code quality
                code_results = check_code_quality(file_path)
                if 'error' not in code_results:
                    results['total_issues'] += len(code_results.get('issues', []))
                
                results['file_results'][file_path] = {
                    'docstring': docstring_results,
                    'code': code_results
                }
    
    return results

def print_quality_report(results: Dict[str, Any]):
    """Print a formatted quality report."""
    print("🔍 **Quality Assessment Report**")
    print("=" * 50)
    
    # Commit quality
    if 'commit_quality' in results and 'error' not in results['commit_quality']:
        cq = results['commit_quality']
        print(f"\n📝 **Commit Quality** ({cq['total_commits']} recent commits)")
        print(f"  ✅ Good format: {cq['good_format']}/{cq['total_commits']} ({cq['good_format']/cq['total_commits']*100:.1f}%)")
        print(f"  ✅ Has setup name: {cq['has_setup_name']}/{cq['total_commits']} ({cq['has_setup_name']/cq['total_commits']*100:.1f}%)")
        print(f"  ✅ Descriptive: {cq['descriptive']}/{cq['total_commits']} ({cq['descriptive']/cq['total_commits']*100:.1f}%)")
        print(f"  ✅ Mentions testing: {cq['mentions_testing']}/{cq['total_commits']} ({cq['mentions_testing']/cq['total_commits']*100:.1f}%)")
        
        if cq['issues']:
            print(f"\n  ⚠️  Issues found:")
            for issue in cq['issues'][:5]:  # Show first 5 issues
                print(f"    - {issue}")
            if len(cq['issues']) > 5:
                print(f"    ... and {len(cq['issues']) - 5} more issues")
    
    # File analysis
    print(f"\n📁 **File Analysis** ({results['files_analyzed']} Python files)")
    print(f"  Total issues found: {results['total_issues']}")
    
    # Show issues by file
    if results['file_results']:
        print(f"\n📋 **Issues by File:**")
        for file_path, file_results in list(results['file_results'].items())[:5]:
            print(f"\n  {file_path}:")
            
            # Docstring issues
            if 'docstring' in file_results and 'issues' in file_results['docstring']:
                for issue in file_results['docstring']['issues'][:3]:
                    print(f"    - {issue}")
            
            # Code issues
            if 'code' in file_results and 'issues' in file_results['code']:
                for issue in file_results['code']['issues'][:3]:
                    print(f"    - {issue}")
    
    # Overall score
    total_checks = results['files_analyzed'] * 4  # Rough estimate
    if total_checks > 0:
        score = max(0, 100 - (results['total_issues'] / total_checks * 100))
        print(f"\n🎯 **Overall Quality Score: {score:.1f}/100**")
        
        if score >= 90:
            print("  🟢 Excellent quality!")
        elif score >= 80:
            print("  🟡 Good quality, minor improvements needed")
        elif score >= 70:
            print("  🟠 Fair quality, several improvements needed")
        else:
            print("  🔴 Poor quality, significant improvements needed")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Assess code quality")
    parser.add_argument('--path', default='src/', help='Path to analyze')
    parser.add_argument('--commits', type=int, default=10, help='Number of commits to check')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.path):
        print(f"Error: Path {args.path} does not exist")
        sys.exit(1)
    
    print(f"Analyzing {args.path}...")
    results = assess_directory(args.path)
    print_quality_report(results)

if __name__ == "__main__":
    main()
