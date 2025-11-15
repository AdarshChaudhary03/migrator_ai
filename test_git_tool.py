"""
Test script for git_tool functionality
Run this to verify that the git_tool is working correctly.
"""

import os
import tempfile
import sys

# Add the project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools.git_tool import create_git_tool

def test_git_tool():
    """Test basic git_tool functionality."""
    print("Testing git_tool functionality...")
    
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    git_tool = create_git_tool(test_dir)
    
    print(f"Created git_tool with base path: {test_dir}")
    
    # Test public repository cloning (no auth needed)
    test_repo_url = "https://github.com/octocat/Hello-World.git"
    success, local_path, error = git_tool.clone_repository(
        git_url=test_repo_url,
        branch="master"
    )
    
    if success:
        print(f"✅ Successfully cloned repository to: {local_path}")
        
        # Test getting commit hash
        hash_success, commit_hash, hash_error = git_tool.get_commit_hash(local_path)
        if hash_success:
            print(f"✅ Current commit hash: {commit_hash}")
        else:
            print(f"❌ Failed to get commit hash: {hash_error}")
        
        # Test getting current branch
        branch_success, branch_name, branch_error = git_tool.get_current_branch(local_path)
        if branch_success:
            print(f"✅ Current branch: {branch_name}")
        else:
            print(f"❌ Failed to get current branch: {branch_error}")
    else:
        print(f"❌ Failed to clone repository: {error}")
    
    print("Git tool test completed!")

if __name__ == "__main__":
    test_git_tool()
