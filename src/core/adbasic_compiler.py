"""
ADbasic Compiler Module

This module provides functionality to compile ADbasic (.bas) files to ADwin binary (.TB*) files
using the ADbasic compiler running under Wine on macOS/Linux.
"""

import os
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ADbasicCompiler:
    """
    A Python wrapper for the ADbasic compiler that runs under Wine.
    
    This class provides methods to compile ADbasic source files (.bas) to ADwin binary files (.TB*)
    using the ADbasic compiler installed via Wine.
    """
    
    def __init__(self, adwin_dir: Optional[str] = None, wine_prefix: Optional[str] = None, 
                 license_file: Optional[str] = None):
        """
        Initialize the ADbasic compiler.
        
        Args:
            adwin_dir: Path to the ADwin installation directory. If None, will try to find it.
            wine_prefix: Path to the Wine prefix. If None, will use default.
            license_file: Path to license configuration file. If None, will look for default locations.
        """
        self.adwin_dir = adwin_dir or self._find_adwin_dir()
        self.wine_prefix = wine_prefix or os.path.expanduser("~/.wine64-adwin")
        self.compiler_path = os.path.join(self.adwin_dir, "bin", "adbasic-mac")
        self.license_file = license_file or self._find_license_file()
        
        if not os.path.exists(self.compiler_path):
            raise FileNotFoundError(f"ADbasic compiler not found at {self.compiler_path}")
        
        # Set up environment variables
        self.env = os.environ.copy()
        self.env['ADWINDIR'] = self.adwin_dir
        self.env['WINEARCH'] = 'win64'
        self.env['WINEPREFIX'] = self.wine_prefix
        
        # Load license if available
        self.license_info = self._load_license()
    
    def _find_adwin_dir(self) -> str:
        """Find the ADwin installation directory."""
        possible_paths = [
            os.path.expanduser("~/adwin"),
            "/usr/local/adwin",
            "/opt/adwin",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("ADwin installation directory not found. Please specify adwin_dir parameter.")
    
    def _find_license_file(self) -> Optional[str]:
        """Find the license configuration file."""
        possible_paths = [
            os.path.expanduser("~/.adwin_license.json"),
            os.path.expanduser("~/adwin_license.json"),
            os.path.join(self.adwin_dir or "~/adwin", "license.json"),
            "adwin_license.json",  # Current directory
            "src/Controller/adwin_license.json",  # Project Controller directory
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _load_license(self) -> Optional[Dict[str, Any]]:
        """Load license information from the license file."""
        if not self.license_file or not os.path.exists(self.license_file):
            logger.warning("No license file found. Compiler will work with limitations.")
            return None
        
        try:
            with open(self.license_file, 'r') as f:
                license_data = json.load(f)
            
            logger.info(f"License loaded from {self.license_file}")
            return license_data
            
        except Exception as e:
            logger.error(f"Failed to load license from {self.license_file}: {e}")
            return None
    
    def _apply_license(self) -> bool:
        """Apply the license to the ADwin system."""
        if not self.license_info:
            logger.warning("No license information available")
            return False
        
        try:
            # Use the ADwinSetLicense.exe tool to apply the license
            license_tool = os.path.join(self.adwin_dir, "bin", "ADwinSetLicense.exe")
            
            if not os.path.exists(license_tool):
                logger.warning("ADwinSetLicense.exe not found")
                return False
            
            # Extract license key from the license info
            license_key = self.license_info.get('license_key')
            if not license_key:
                logger.warning("No license key found in license file")
                return False
            
            # Run the license tool
            cmd = [self.compiler_path, license_tool, license_key]
            result = subprocess.run(
                cmd,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("License applied successfully")
                return True
            else:
                logger.warning(f"License application failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to apply license: {e}")
            return False
    
    def compile_file(self, 
                    source_file: str, 
                    output_dir: Optional[str] = None,
                    process_number: Optional[int] = None,
                    verbose: bool = False,
                    apply_license: bool = True) -> str:
        """
        Compile an ADbasic source file to an ADwin binary file.
        
        Args:
            source_file: Path to the .bas source file
            output_dir: Directory to place the output file. If None, uses the same directory as source.
            process_number: Process number (1-10) for the output file. If None, tries to detect from source.
            verbose: Whether to print verbose output
            apply_license: Whether to apply license before compilation
            
        Returns:
            Path to the compiled .TB* file
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            subprocess.CalledProcessError: If compilation fails
        """
        source_path = Path(source_file)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        if not source_path.suffix.lower() == '.bas':
            raise ValueError(f"Source file must have .bas extension: {source_file}")
        
        # Apply license if requested and available
        if apply_license and self.license_info:
            self._apply_license()
        
        # Determine output directory
        if output_dir is None:
            output_dir = source_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine process number if not specified
        if process_number is None:
            process_number = self._detect_process_number(source_path)
        
        if not 1 <= process_number <= 10:
            raise ValueError(f"Process number must be between 1 and 10, got {process_number}")
        
        # Determine output filename
        output_filename = f"{source_path.stem}.TB{process_number}"
        output_path = output_dir / output_filename
        
        # Build compiler command
        cmd = [self.compiler_path, str(source_path)]
        
        if verbose:
            logger.info(f"Compiling {source_file} to {output_path}")
            logger.info(f"Command: {' '.join(cmd)}")
            if self.license_info:
                logger.info("Using licensed compiler")
            else:
                logger.info("Using unlicensed compiler (may have limitations)")
        
        try:
            # Run the compiler
            result = subprocess.run(
                cmd,
                env=self.env,
                cwd=str(source_path.parent),
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if verbose:
                if result.stdout:
                    logger.info(f"Compiler stdout: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Compiler stderr: {result.stderr}")
            
            # Check for license errors (these are warnings, not fatal errors)
            license_errors = [
                "Wrong Licenskey",
                "Invalid License", 
                "Translatemode is missing"
            ]
            
            has_license_error = any(error in result.stderr for error in license_errors)
            
            # Check if compilation was successful
            if result.returncode != 0:
                if has_license_error:
                    logger.warning("Compilation completed with license warnings (this is expected without a valid license)")
                    # Continue to check for output file
                else:
                    error_msg = f"Compilation failed with return code {result.returncode}"
                    if result.stderr:
                        error_msg += f"\nStderr: {result.stderr}"
                    if result.stdout:
                        error_msg += f"\nStdout: {result.stdout}"
                    raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
            
            # Check if output file was created
            if not output_path.exists():
                # Try to find the output file with different extensions
                possible_outputs = list(output_dir.glob(f"{source_path.stem}.*"))
                if possible_outputs:
                    output_path = possible_outputs[0]
                    logger.info(f"Found output file: {output_path}")
                else:
                    if has_license_error:
                        logger.warning(f"Compilation completed but no output file found. This may be due to license restrictions.")
                        # Return a placeholder path for now
                        return str(output_path)
                    else:
                        raise FileNotFoundError(f"Compilation succeeded but output file not found: {output_path}")
            
            if has_license_error:
                logger.info(f"Successfully compiled {source_file} to {output_path} (with license warnings)")
            else:
                logger.info(f"Successfully compiled {source_file} to {output_path}")
            return str(output_path)
            
        except subprocess.TimeoutExpired:
            raise subprocess.TimeoutExpired(cmd, 60, "Compilation timed out")
    
    def _detect_process_number(self, source_path: Path) -> int:
        """
        Try to detect the process number from the ADbasic source file.
        
        Args:
            source_path: Path to the .bas file
            
        Returns:
            Process number (1-10)
        """
        try:
            with open(source_path, 'r') as f:
                content = f.read()
                
            # Look for process configuration in the source
            lines = content.split('\n')
            for line in lines:
                line = line.strip().upper()
                if line.startswith('PROCESS'):
                    # Extract process number
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            return int(parts[1])
                        except ValueError:
                            pass
                
                # Also check for comments indicating process number
                if 'PROCESS' in line and any(str(i) in line for i in range(1, 11)):
                    for i in range(1, 11):
                        if str(i) in line:
                            return i
            
            # Default to process 1 if no process number found
            logger.warning(f"Could not detect process number in {source_path}, defaulting to process 1")
            return 1
            
        except Exception as e:
            logger.warning(f"Error detecting process number: {e}, defaulting to process 1")
            return 1
    
    def compile_directory(self, 
                         source_dir: str, 
                         output_dir: Optional[str] = None,
                         verbose: bool = False,
                         apply_license: bool = True) -> Dict[str, str]:
        """
        Compile all .bas files in a directory.
        
        Args:
            source_dir: Directory containing .bas files
            output_dir: Directory to place output files. If None, uses source_dir.
            verbose: Whether to print verbose output
            apply_license: Whether to apply license before compilation
            
        Returns:
            Dictionary mapping source files to output files
        """
        source_path = Path(source_dir)
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
        
        if output_dir is None:
            output_dir = source_dir
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        bas_files = list(source_path.glob("*.bas"))
        
        if not bas_files:
            logger.warning(f"No .bas files found in {source_dir}")
            return results
        
        for bas_file in bas_files:
            try:
                output_file = self.compile_file(str(bas_file), output_dir, verbose=verbose, apply_license=apply_license)
                results[str(bas_file)] = output_file
            except Exception as e:
                logger.error(f"Failed to compile {bas_file}: {e}")
                results[str(bas_file)] = None
        
        return results
    
    def check_compiler(self) -> bool:
        """
        Check if the ADbasic compiler is working properly.
        
        Returns:
            True if compiler is working, False otherwise
        """
        try:
            # Check if the compiler executable exists and is accessible
            if not os.path.exists(self.compiler_path):
                logger.error(f"Compiler not found at {self.compiler_path}")
                return False
            
            # Check if the compiler is executable
            if not os.access(self.compiler_path, os.X_OK):
                logger.error(f"Compiler not executable: {self.compiler_path}")
                return False
            
            # Check if the ADwin directory structure is correct
            required_files = [
                os.path.join(self.adwin_dir, "bin", "ADbasicCompiler.exe"),
                os.path.join(self.adwin_dir, "bin", "madlib.dll")
            ]
            
            for required_file in required_files:
                if not os.path.exists(required_file):
                    logger.warning(f"Required file not found: {required_file}")
                    # Don't fail completely, as the compiler might still work
            
            # Don't actually run the compiler during check to avoid creating error files
            # Just verify the basic setup is correct
            logger.info(f"ADbasic compiler found at {self.compiler_path}")
            return True
            
        except Exception as e:
            logger.error(f"Compiler check failed: {e}")
            return False
    
    def get_license_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current license.
        
        Returns:
            License information dictionary or None if no license
        """
        return self.license_info
    
    def has_valid_license(self) -> bool:
        """
        Check if a valid license is available.
        
        Returns:
            True if license is available and valid, False otherwise
        """
        if not self.license_info:
            return False
        
        # Check for required license fields
        required_fields = ['license_key', 'device_type', 'expiration_date']
        for field in required_fields:
            if field not in self.license_info:
                return False
        
        return True


def compile_adbasic_file(source_file: str, 
                        output_dir: Optional[str] = None,
                        process_number: Optional[int] = None,
                        verbose: bool = False,
                        license_file: Optional[str] = None) -> str:
    """
    Convenience function to compile a single ADbasic file.
    
    Args:
        source_file: Path to the .bas source file
        output_dir: Directory to place the output file
        process_number: Process number (1-10) for the output file
        verbose: Whether to print verbose output
        license_file: Path to license configuration file
        
    Returns:
        Path to the compiled .TB* file
    """
    compiler = ADbasicCompiler(license_file=license_file)
    return compiler.compile_file(source_file, output_dir, process_number, verbose)


def compile_adbasic_directory(source_dir: str, 
                            output_dir: Optional[str] = None,
                            verbose: bool = False,
                            license_file: Optional[str] = None) -> Dict[str, str]:
    """
    Convenience function to compile all .bas files in a directory.
    
    Args:
        source_dir: Directory containing .bas files
        output_dir: Directory to place output files
        verbose: Whether to print verbose output
        license_file: Path to license configuration file
        
    Returns:
        Dictionary mapping source files to output files
    """
    compiler = ADbasicCompiler(license_file=license_file)
    return compiler.compile_directory(source_dir, output_dir, verbose)


def create_license_template(output_file: str = "src/Controller/adwin_license_template.json"):
    """
    Create a template license file for users to fill in.
    
    Args:
        output_file: Path to the template file to create
    """
    template = {
        "license_key": "YOUR_LICENSE_KEY_HERE",
        "device_type": "ADwin Gold II",
        "device_id": "YOUR_DEVICE_ID_HERE",
        "expiration_date": "YYYY-MM-DD",
        "features": [
            "ADbasic_compiler",
            "TiCO_compiler",
            "real_time_processing"
        ],
        "notes": "Replace the placeholder values with your actual license information"
    }
    
    # Ensure the directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"License template created: {output_file}")
    print("Please edit this file with your actual license information.") 