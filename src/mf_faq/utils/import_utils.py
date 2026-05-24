"""
Safe Import Utilities
Provides functions to safely check if heavy/ML libraries can be imported 
without triggering silent DLL crashes (common on Windows without MSVC Redistributable).
"""

import os
import sys
import subprocess
import logging

logger = logging.getLogger(__name__)

# Cache for check results
_IMPORT_CACHE = {}

def is_library_safe(lib_name: str) -> bool:
    """
    Check if a library is safe to import.
    Runs a lightweight python check in a subprocess to catch silent DLL load failures
    that bypass standard try-except blocks in the main process.
    """
    # Check cache first
    if lib_name in _IMPORT_CACHE:
        return _IMPORT_CACHE[lib_name]
        
    # Check env override
    if os.environ.get(f"DISABLE_{lib_name.upper()}") == "1" or os.environ.get("DISABLE_ML_COMPONENTS") == "1":
        logger.warning(f"Library {lib_name} is disabled via environment variables.")
        _IMPORT_CACHE[lib_name] = False
        return False
        
    try:
        # Run a quick check in a subprocess
        cmd = [sys.executable, "-X", "utf8", "-c", f"import {lib_name}"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=10
        )
        
        is_safe = (result.returncode == 0)
        
        if not is_safe:
            logger.warning(
                f"Library '{lib_name}' failed to import in subprocess (exit code {result.returncode}).\n"
                f"Stdout: {result.stdout.decode('utf-8', errors='ignore')}\n"
                f"Stderr: {result.stderr.decode('utf-8', errors='ignore')}\n"
                f"Falling back to Mock implementation."
            )
            
        _IMPORT_CACHE[lib_name] = is_safe
        return is_safe
        
    except Exception as e:
        logger.warning(f"Error checking import safety for {lib_name}: {e}. Defaulting to unsafe/False.")
        _IMPORT_CACHE[lib_name] = False
        return False
