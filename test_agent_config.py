#!/usr/bin/env python3
"""
Test script to verify that agents can load with environment-based model configuration.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables for testing
os.environ['LLM_MODEL'] = 'gemini-2.0-flash'
os.environ['LLM_TEMPERATURE'] = '0.2'
os.environ['LLM_MAX_TOKENS'] = '8192'

def test_model_config():
    """Test that model configuration loads correctly."""
    print("Testing model configuration...")
    
    try:
        from utils.model_config import get_llm_model, get_model_config
        
        # Test model loading
        model = get_llm_model()
        print(f"✅ Model loaded successfully: {type(model).__name__}")
        
        # Test config loading
        config = get_model_config()
        print(f"✅ Model config loaded: {config}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model config test failed: {e}")
        return False

def test_agent_import():
    """Test that agents can be imported without errors."""
    print("\nTesting agent imports...")
    
    try:
        # Test importing an agent
        from agents.scanner_analyzer.agent import ScannerAnalyzerAgent
        print("✅ Scanner analyzer agent imported successfully")
        
        # Test creating an agent instance
        agent = ScannerAnalyzerAgent()
        print("✅ Agent instance created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent import test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Agent Configuration Test ===")
    
    test1_passed = test_model_config()
    test2_passed = test_agent_import()
    
    if test1_passed and test2_passed:
        print("\n✅ All configuration tests passed!")
        print("The migration system should work with environment-based model configuration.")
        sys.exit(0)
    else:
        print("\n❌ Some configuration tests failed.")
        sys.exit(1)
