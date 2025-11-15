"""
Git Tool for Repository Cloning and Management
Provides standalone functions for Git operations, ZIP file handling, and repository validation.
"""

import os
import subprocess
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clone_repository(
    git_url: str, 
    branch: str = "main", 
    credentials: Optional[Dict[str, str]] = None,
    local_path: Optional[str] = None,
    base_path: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Clone a Git repository from the provided URL.
    
    Args:
        git_url: The Git repository URL (HTTPS or SSH)
        branch: The branch to clone (default: "main")
        credentials: Optional credentials dict with 'username' and 'password'/'token'
        local_path: Optional local path. If None, generates one based on repo name
        base_path: Base directory for operations. If None, uses temp directory
        
    Returns:
        Tuple of (success: bool, local_path: str, error_message: str)
    """
    try:
        # Set base path if not provided
        if not base_path:
            base_path = tempfile.gettempdir()
        os.makedirs(base_path, exist_ok=True)
        
        # Generate local path if not provided
        if not local_path:
            repo_name = extract_repo_name(git_url)
            local_path = os.path.join(base_path, repo_name)
        
        # Remove existing directory if it exists
        if os.path.exists(local_path):
            shutil.rmtree(local_path)
        
        # Prepare git clone command
        cmd = ["git", "clone", "--branch", branch, git_url, local_path]
        
        # Set up environment for credentials
        env = os.environ.copy()
        if credentials:
            if git_url.startswith("https://"):
                # For HTTPS, modify the URL to include credentials
                parsed_url = urlparse(git_url)
                if credentials.get("username") and credentials.get("password"):
                    auth_url = f"{parsed_url.scheme}://{credentials['username']}:{credentials['password']}@{parsed_url.netloc}{parsed_url.path}"
                    cmd[3] = auth_url  # Replace the original URL
            
            # Set environment variables for Git credentials
            if credentials.get("username"):
                env["GIT_USERNAME"] = credentials["username"]
            if credentials.get("password"):
                env["GIT_PASSWORD"] = credentials["password"]
            if credentials.get("token"):
                env["GIT_TOKEN"] = credentials["token"]
        
        # Execute git clone
        logger.info(f"Cloning repository from {git_url} to {local_path}")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            env=env,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            error_msg = f"Git clone failed: {result.stderr}"
            logger.error(error_msg)
            return False, local_path, error_msg
        
        # Validate the cloned repository
        validation_success, validation_error = validate_repository(local_path, branch)
        if not validation_success:
            return False, local_path, validation_error
        
        logger.info(f"Successfully cloned repository to {local_path}")
        return True, local_path, ""
        
    except subprocess.TimeoutExpired:
        error_msg = "Git clone operation timed out"
        logger.error(error_msg)
        return False, local_path, error_msg
    except Exception as e:
        error_msg = f"Exception during git clone: {str(e)}"
        logger.error(error_msg)
        return False, local_path, error_msg


def handle_zip_upload(
    zip_file_path: str, 
    extract_path: Optional[str] = None,
    base_path: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Handle uploaded ZIP file by extracting and initializing as Git repository.
    
    Args:
        zip_file_path: Path to the ZIP file
        extract_path: Optional extraction path. If None, generates one
        base_path: Base directory for operations. If None, uses temp directory
        
    Returns:
        Tuple of (success: bool, local_path: str, error_message: str)
    """
    try:
        if not os.path.exists(zip_file_path):
            error_msg = f"ZIP file not found: {zip_file_path}"
            logger.error(error_msg)
            return False, "", error_msg
        
        # Set base path if not provided
        if not base_path:
            base_path = tempfile.gettempdir()
        os.makedirs(base_path, exist_ok=True)
        
        # Generate extraction path if not provided
        if not extract_path:
            zip_name = Path(zip_file_path).stem
            extract_path = os.path.join(base_path, zip_name)
        
        # Remove existing directory if it exists
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        
        # Extract ZIP file
        logger.info(f"Extracting ZIP file {zip_file_path} to {extract_path}")
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Initialize Git repository
        git_init_success, git_error = initialize_git_repository(extract_path)
        if not git_init_success:
            return False, extract_path, git_error
        
        logger.info(f"Successfully extracted and initialized repository at {extract_path}")
        return True, extract_path, ""
        
    except zipfile.BadZipFile:
        error_msg = f"Invalid ZIP file: {zip_file_path}"
        logger.error(error_msg)
        return False, extract_path, error_msg
    except Exception as e:
        error_msg = f"Exception during ZIP extraction: {str(e)}"
        logger.error(error_msg)
        return False, extract_path, error_msg


def get_commit_hash(repo_path: str) -> Tuple[bool, str, str]:
    """
    Get the current commit hash of the repository.
    
    Args:
        repo_path: Path to the Git repository
        
    Returns:
        Tuple of (success: bool, commit_hash: str, error_message: str)
    """
    try:
        cmd = ["git", "-C", repo_path, "rev-parse", "HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = f"Failed to get commit hash: {result.stderr}"
            logger.error(error_msg)
            return False, "", error_msg
        
        commit_hash = result.stdout.strip()
        logger.info(f"Current commit hash: {commit_hash}")
        return True, commit_hash, ""
        
    except Exception as e:
        error_msg = f"Exception getting commit hash: {str(e)}"
        logger.error(error_msg)
        return False, "", error_msg


def get_current_branch(repo_path: str) -> Tuple[bool, str, str]:
    """
    Get the current branch of the repository.
    
    Args:
        repo_path: Path to the Git repository
        
    Returns:
        Tuple of (success: bool, branch_name: str, error_message: str)
    """
    try:
        cmd = ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = f"Failed to get current branch: {result.stderr}"
            logger.error(error_msg)
            return False, "", error_msg
        
        branch_name = result.stdout.strip()
        logger.info(f"Current branch: {branch_name}")
        return True, branch_name, ""
        
    except Exception as e:
        error_msg = f"Exception getting current branch: {str(e)}"
        logger.error(error_msg)
        return False, "", error_msg


def extract_repo_name(git_url: str) -> str:
    """Extract repository name from Git URL."""
    # Remove .git suffix if present
    url = git_url.rstrip('/')
    if url.endswith('.git'):
        url = url[:-4]
    
    # Extract the last part of the path
    return os.path.basename(url)


def validate_repository(repo_path: str, expected_branch: str) -> Tuple[bool, str]:
    """
    Validate that the repository was cloned correctly.
    
    Args:
        repo_path: Path to the repository
        expected_branch: Expected branch name
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        # Check if directory exists
        if not os.path.exists(repo_path):
            return False, f"Repository directory does not exist: {repo_path}"
        
        # Check if it's a git repository
        git_dir = os.path.join(repo_path, '.git')
        if not os.path.exists(git_dir):
            return False, f"Not a git repository: {repo_path}"
        
        # Check if the correct branch is checked out
        success, current_branch, error = get_current_branch(repo_path)
        if not success:
            return False, f"Failed to verify branch: {error}"
        
        if current_branch != expected_branch:
            logger.warning(f"Expected branch '{expected_branch}' but got '{current_branch}'")
        
        # Check if there are any files in the repository
        files = os.listdir(repo_path)
        source_files = [f for f in files if not f.startswith('.git')]
        if not source_files:
            return False, "Repository appears to be empty"
        
        return True, ""
        
    except Exception as e:
        return False, f"Exception during validation: {str(e)}"


def initialize_git_repository(repo_path: str) -> Tuple[bool, str]:
    """
    Initialize a Git repository and make an initial commit.
    
    Args:
        repo_path: Path to initialize as Git repository
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        # Initialize git repository
        cmd_init = ["git", "-C", repo_path, "init"]
        result = subprocess.run(cmd_init, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, f"Git init failed: {result.stderr}"
        
        # Add all files
        cmd_add = ["git", "-C", repo_path, "add", "."]
        result = subprocess.run(cmd_add, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, f"Git add failed: {result.stderr}"
        
        # Make initial commit
        cmd_commit = ["git", "-C", repo_path, "commit", "-m", "Initial commit from ZIP"]
        result = subprocess.run(cmd_commit, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, f"Git commit failed: {result.stderr}"
        
        logger.info(f"Successfully initialized Git repository at {repo_path}")
        return True, ""
        
    except Exception as e:
        return False, f"Exception during Git initialization: {str(e)}"
