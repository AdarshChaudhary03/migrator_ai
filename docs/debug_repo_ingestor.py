#!/usr/bin/env python3
"""
Test script to debug the repo_ingestor behavior in the sequential workflow
"""

import os
import sys
import json

# Add the project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agents.repo_ingestor.agent import repo_ingestor_agent

def test_repo_ingestor():
    """Test the repo_ingestor agent directly"""
    print("Testing repo_ingestor_agent directly...")
    
    # Test with a simple Spring Boot repository
    test_repo = "https://github.com/spring-guides/gs-spring-boot.git"
    
    print(f"Input: {test_repo}")
    
    try:
        # Check what methods are available on the agent
        print(f"Agent type: {type(repo_ingestor_agent)}")
        print(f"Agent methods: {[method for method in dir(repo_ingestor_agent) if not method.startswith('_')]}")
        
        # Try to invoke the agent using run_live
        print("Attempting to use run_live method...")
        result = repo_ingestor_agent.run_live(test_repo)
        
        print(f"Agent execution result type: {type(result)}")
        print(f"Result: {result}")
        
        # Check if the repository was cloned
        print("\nChecking output directory:")
        output_dir = "./output"
        if os.path.exists(output_dir):
            contents = os.listdir(output_dir)
            print(f"Output directory contents: {contents}")
            
            # Look for the cloned repository
            repo_name = "gs-spring-boot"
            if repo_name in contents:
                print(f"✅ Repository {repo_name} found in output directory")
                repo_path = os.path.join(output_dir, repo_name)
                repo_contents = os.listdir(repo_path)[:10]  # First 10 items
                print(f"Repository contents (first 10): {repo_contents}")
            else:
                print(f"❌ Repository {repo_name} NOT found in output directory")
        else:
            print(f"❌ Output directory {output_dir} does not exist")
            
    except Exception as e:
        print(f"Error during agent execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_repo_ingestor()
