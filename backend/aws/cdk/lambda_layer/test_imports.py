#!/usr/bin/env python3
"""
Test script to validate Lambda layer imports.

Tests that all required dependencies can be imported successfully
in Python 3.11 runtime.
"""

import sys
import os

# Add layer path to Python path
layer_path = os.path.join(os.path.dirname(__file__), "build", "python")
sys.path.insert(0, layer_path)

def test_imports() -> None:
    """Test that all layer dependencies can be imported."""
    print("Testing Lambda layer imports for Python 3.11...")
    
    try:
        # Test scipy
        print("  Testing scipy...", end=" ")
        import scipy
        import scipy.optimize
        print(f"✓ (version {scipy.__version__})")
        
        # Test numpy
        print("  Testing numpy...", end=" ")
        import numpy
        print(f"✓ (version {numpy.__version__})")
        
        # Test gremlin_python
        print("  Testing gremlin_python...", end=" ")
        from gremlin_python.driver import client
        from gremlin_python.process.traversal import T
        print("✓")
        
        # Test pydantic
        print("  Testing pydantic...", end=" ")
        from pydantic import BaseModel, Field
        print(f"✓ (version {BaseModel.__module__.split('.')[0]})")
        
        # Test structlog
        print("  Testing structlog...", end=" ")
        import structlog
        print("✓")
        
        print("\n✅ All imports successful!")
        print(f"Python version: {sys.version}")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
