#!/usr/bin/env python3
"""
Test script to verify JSON serialization works after subprocess fixes.
"""

import json
import subprocess
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils.subprocess_utils import safe_decode_output, ensure_json_serializable

def test_subprocess_output_handling():
    """Test that subprocess output is properly handled."""
    print("Testing subprocess output handling...")
    
    # Simulate a subprocess call that returns bytes
    try:
        result = subprocess.run(
            ["echo", "test output"], 
            capture_output=True,
            text=False  # Force bytes output
        )
        
        # Test safe_decode_output function
        decoded = safe_decode_output(result.stdout)
        print(f"Decoded output: '{decoded}' (type: {type(decoded)})")
        
        # Test JSON serialization of the decoded output
        test_dict = {
            "output": decoded,
            "success": True,
            "returncode": result.returncode
        }
        
        # This should not raise an exception
        json_str = json.dumps(test_dict)
        print(f"JSON serialization successful: {json_str[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False

def test_ensure_json_serializable():
    """Test the ensure_json_serializable function."""
    print("\nTesting ensure_json_serializable function...")
    
    try:
        # Test with various data types
        test_data = {
            "string": "test",
            "number": 42,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
            "bytes": b"test bytes",  # This should be converted
            "nested": {
                "more_bytes": b"nested bytes"
            }
        }
        
        # This should clean up any non-serializable objects
        clean_data = ensure_json_serializable(test_data)
        
        # Test JSON serialization
        json_str = json.dumps(clean_data)
        print(f"Clean data JSON serialization successful: {json_str[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== JSON Serialization Test ===")
    
    test1_passed = test_subprocess_output_handling()
    test2_passed = test_ensure_json_serializable()
    
    if test1_passed and test2_passed:
        print("\n✅ All tests passed! JSON serialization should work correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. There may still be JSON serialization issues.")
        sys.exit(1)
