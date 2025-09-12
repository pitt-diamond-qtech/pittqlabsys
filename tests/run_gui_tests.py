#!/usr/bin/env python3
"""
GUI Test Runner for AQuISS.
This script runs all GUI-related tests with proper configuration and reporting.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def run_gui_tests():
    """Run all GUI tests with proper configuration"""
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Change to project root
    os.chdir(project_root)
    
    print("=" * 60)
    print("AQuISS GUI Test Suite")
    print("=" * 60)
    print(f"Project root: {project_root}")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print()
    
    # Test files to run
    test_files = [
        "tests/test_gui_basic.py",
        "tests/test_gui_stress.py", 
        "tests/test_gui_buttons.py",
        "tests/test_gui_trees.py"
    ]
    
    # Check if test files exist
    missing_tests = []
    for test_file in test_files:
        if not Path(test_file).exists():
            missing_tests.append(test_file)
    
    if missing_tests:
        print("Warning: Some test files are missing:")
        for test in missing_tests:
            print(f"  - {test}")
        print()
    
    # Run each test file
    results = {}
    total_tests = 0
    total_passed = 0
    total_failed = 0
    
    for test_file in test_files:
        if not Path(test_file).exists():
            continue
            
        print(f"Running {test_file}...")
        print("-" * 40)
        
        try:
            # Run pytest with verbose output
            cmd = [
                sys.executable, "-m", "pytest",
                test_file,
                "-v",
                "--tb=short",
                "--color=yes"
            ]
            
            # Run the test
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test file
            )
            end_time = time.time()
            
            # Parse results
            output_lines = result.stdout.split('\n')
            test_summary = None
            
            for line in output_lines:
                if 'passed' in line and 'failed' in line:
                    test_summary = line
                    break
            
            # Extract test counts
            if test_summary:
                if 'passed' in test_summary:
                    passed = int(test_summary.split('passed')[0].split()[-1])
                else:
                    passed = 0
                    
                if 'failed' in test_summary:
                    failed = int(test_summary.split('failed')[0].split()[-1])
                else:
                    failed = 0
                    
                total = passed + failed
            else:
                passed = failed = total = 0
            
            # Store results
            results[test_file] = {
                'return_code': result.return_code,
                'passed': passed,
                'failed': failed,
                'total': total,
                'duration': end_time - start_time,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            total_tests += total
            total_passed += passed
            total_failed += failed
            
            # Print results
            if result.return_code == 0:
                print(f"✅ PASSED: {passed}/{total} tests passed in {end_time - start_time:.2f}s")
            else:
                print(f"❌ FAILED: {failed}/{total} tests failed in {end_time - start_time:.2f}s")
                
            if result.stderr:
                print("Errors/Warnings:")
                for line in result.stderr.split('\n')[:5]:  # Show first 5 error lines
                    if line.strip():
                        print(f"  {line}")
                        
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: Test file {test_file} exceeded 5 minute timeout")
            results[test_file] = {
                'return_code': -1,
                'passed': 0,
                'failed': 0,
                'total': 0,
                'duration': 300,
                'stdout': '',
                'stderr': 'Test timeout'
            }
            total_failed += 1
            
        except Exception as e:
            print(f"💥 ERROR: Failed to run {test_file}: {e}")
            results[test_file] = {
                'return_code': -1,
                'passed': 0,
                'failed': 0,
                'total': 0,
                'duration': 0,
                'stdout': '',
                'stderr': str(e)
            }
            total_failed += 1
            
        print()
    
    # Print summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_file, result in results.items():
        status = "✅ PASS" if result['return_code'] == 0 else "❌ FAIL"
        print(f"{status} {test_file}: {result['passed']}/{result['total']} passed in {result['duration']:.2f}s")
    
    print()
    print(f"Total Tests: {total_tests}")
    print(f"Total Passed: {total_passed}")
    print(f"Total Failed: {total_failed}")
    print(f"Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "Success Rate: N/A")
    
    # Return overall success
    return total_failed == 0

def run_specific_test(test_name):
    """Run a specific test by name"""
    test_file = f"tests/test_gui_{test_name}.py"
    
    if not Path(test_file).exists():
        print(f"Test file {test_file} not found!")
        return False
    
    print(f"Running specific test: {test_file}")
    print("-" * 40)
    
    cmd = [
        sys.executable, "-m", "pytest",
        test_file,
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    try:
        result = subprocess.run(cmd, timeout=300)
        return result.return_code == 0
    except subprocess.TimeoutExpired:
        print("Test timeout!")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
    else:
        # Run all tests
        success = run_gui_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
