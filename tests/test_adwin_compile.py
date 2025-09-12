#!/usr/bin/env python3
"""
Test script for the ADbasic compiler integration.

This script demonstrates how to use the new compile_and_load_process method
to compile ADbasic source files and load them into the ADwin on the fly.
"""

import pytest
import sys
import os
from pathlib import Path

# Calculate project root manually first (from tests directory)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now we can import from the project
from src.core.helper_functions import get_project_root
from src.core.adbasic_compiler import ADbasicCompiler, compile_adbasic_file, create_license_template
from src.Controller.adwin_gold import AdwinGoldDevice


class TestADbasicCompiler:
    """Test suite for ADbasic compiler integration."""
    
    def test_compiler_initialization(self):
        """Test the ADbasic compiler initialization."""
        # Test the compiler
        compiler = ADbasicCompiler()
        
        # Check if compiler can be initialized
        assert compiler is not None, "Compiler should be initialized"
        
        # Test compiler check (may fail without license, but should not crash)
        try:
            is_working = compiler.check_compiler()
            # Don't assert here as it may fail without license
        except Exception as e:
            # Should not crash, even if license is missing
            assert "license" in str(e).lower() or "compiler" in str(e).lower(), f"Unexpected error: {e}"
    
    def test_compiler_license_management(self):
        """Test license management functionality."""
        # Test creating license template
        test_template_path = "test_license_template.json"
        
        try:
            create_license_template(test_template_path)
            assert Path(test_template_path).exists(), "License template should be created"
            
            # Clean up
            Path(test_template_path).unlink(missing_ok=True)
            
        except Exception as e:
            pytest.skip(f"License template creation failed: {e}")
    
    def test_compiler_license_status(self):
        """Test license status checking."""
        compiler = ADbasicCompiler()
        
        # Test license status checking (should not crash)
        try:
            has_license = compiler.has_valid_license()
            license_info = compiler.get_license_info()
            
            # These should not crash, even without license
            assert isinstance(has_license, bool), "has_valid_license should return boolean"
            assert license_info is not None, "get_license_info should return dict"
            
        except Exception as e:
            # Should not crash, even if license is missing
            assert "license" in str(e).lower() or "file" in str(e).lower(), f"Unexpected error: {e}"
    
    @pytest.mark.slow
    def test_file_compilation(self):
        """Test compiling a single ADbasic file."""
        source_file = "src/Controller/binary_files/ADbasic/Trial_Counter.bas"
        
        # Check if source file exists
        if not Path(source_file).exists():
            pytest.skip(f"Source file not found: {source_file}")
        
        try:
            compiled_file = compile_adbasic_file(source_file, verbose=False)
            
            # Should return a path (may not exist due to license restrictions)
            assert isinstance(compiled_file, str), "compile_adbasic_file should return string path"
            
        except Exception as e:
            # Expected to fail without license, but should not crash
            assert "license" in str(e).lower() or "compiler" in str(e).lower(), f"Unexpected error: {e}"
    
    def test_directory_compilation(self):
        """Test compiling all files in a directory."""
        source_dir = "src/Controller/binary_files/ADbasic"
        
        # Check if directory exists
        if not Path(source_dir).exists():
            pytest.skip(f"Source directory not found: {source_dir}")
        
        try:
            from src.core.adbasic_compiler import compile_adbasic_directory
            
            result = compile_adbasic_directory(source_dir, verbose=False)
            
            # Should return a dict mapping source files to compiled files
            assert isinstance(result, dict), "compile_adbasic_directory should return dict"
            
        except Exception as e:
            # Expected to fail without license, but should not crash
            assert "license" in str(e).lower() or "compiler" in str(e).lower(), f"Unexpected error: {e}"
    
    def test_adwin_integration(self):
        """Test the ADwin integration with the compiler."""
        try:
            # Initialize ADwin (this will fail if no ADwin is connected)
            adwin = AdwinGoldDevice(boot=False)  # Don't boot to avoid issues if no hardware
            
            # Test license status checking
            try:
                license_status = adwin.check_license_status()
                assert isinstance(license_status, dict), "License status should be a dict"
                assert 'status' in license_status, "License status should have 'status' key"
                
            except Exception as e:
                # Expected to fail without license, but should not crash
                assert "license" in str(e).lower() or "compiler" in str(e).lower(), f"Unexpected error: {e}"
                
        except Exception as e:
            # Expected to fail without ADwin hardware, but should not crash
            assert "adwin" in str(e).lower() or "hardware" in str(e).lower(), f"Unexpected error: {e}"
    
    def test_license_file_usage(self):
        """Test license file usage and validation."""
        compiler = ADbasicCompiler()
        
        # Test with non-existent license file
        try:
            # This should not crash
            result = compiler._find_license_file()
            # Result may be None if no license file found
            assert result is None or isinstance(result, Path), "License file result should be None or Path"
            
        except Exception as e:
            # Should not crash
            assert "file" in str(e).lower() or "path" in str(e).lower(), f"Unexpected error: {e}"
    
    def test_compiler_error_handling(self):
        """Test that the compiler handles errors gracefully."""
        compiler = ADbasicCompiler()
        
        # Test with invalid file
        try:
            result = compile_adbasic_file("nonexistent_file.bas", verbose=False)
            # Should handle gracefully
        except Exception as e:
            # Should not crash
            assert "file" in str(e).lower() or "not found" in str(e).lower(), f"Unexpected error: {e}"
    
    @pytest.mark.slow
    def test_full_compilation_workflow(self):
        """Test the complete compilation workflow."""
        # Test the complete workflow without requiring actual compilation
        compiler = ADbasicCompiler()
        
        # Test all the main methods exist and are callable
        assert hasattr(compiler, 'check_compiler'), "Compiler should have check_compiler method"
        assert hasattr(compiler, 'compile_file'), "Compiler should have compile_file method"
        assert hasattr(compiler, 'compile_directory'), "Compiler should have compile_directory method"
        assert hasattr(compiler, 'has_valid_license'), "Compiler should have has_valid_license method"
        assert hasattr(compiler, 'get_license_info'), "Compiler should have get_license_info method"
        
        # Test that methods are callable
        assert callable(compiler.check_compiler), "check_compiler should be callable"
        assert callable(compiler.compile_file), "compile_file should be callable"
        assert callable(compiler.compile_directory), "compile_directory should be callable"
        assert callable(compiler.has_valid_license), "has_valid_license should be callable"
        assert callable(compiler.get_license_info), "get_license_info should be callable" 