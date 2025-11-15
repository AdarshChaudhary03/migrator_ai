import os
import subprocess
import shutil
from typing import Dict, Any, Optional
from pathlib import Path
import uuid
import json
import logging

from utils.subprocess_utils import safe_decode_output, ensure_json_serializable

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def clone_repo(repo_url: str, output_dir: str = "./output", repo_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Clone a GitHub repository to a local directory.
    
    Args:
        repo_url (str): The GitHub repository URL to clone
        output_dir (str): The base directory where the repo will be cloned (default: "./output")
        repo_name (str, optional): Custom name for the cloned directory. If None, extracts from URL
    
    Returns:
        Dict[str, Any]: A dictionary containing clone operation results and metadata
    """
    logger.info(f"Starting clone_repo function with repo_url: {repo_url}, output_dir: {output_dir}")
    
    try:
        # Validate the repository URL
        logger.info(f"Validating repository URL: {repo_url}")
        if not repo_url or not isinstance(repo_url, str):
            error_result = {
                "success": False,
                "error": "Invalid repository URL provided",
                "repo_url": repo_url,
                "local_path": None
            }
            logger.error(f"URL validation failed: {error_result}")
            return error_result
        
        # Extract repository name from URL if not provided
        if repo_name is None:
            if repo_url.endswith('.git'):
                repo_name = repo_url.split('/')[-1][:-4]  # Remove .git extension
            else:
                repo_name = repo_url.split('/')[-1]
        
        logger.info(f"Repository name extracted: {repo_name}")
        
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory created/verified: {output_path}")
        
        # Full path for the cloned repository
        local_path = output_path / repo_name
        logger.info(f"Target local path: {local_path}")
        
        # Remove existing directory if it exists
        if local_path.exists():
            logger.info(f"Removing existing directory: {local_path}")
            shutil.rmtree(local_path)
        
        # Execute git clone command
        clone_cmd = ["git", "clone", repo_url, str(local_path)]
        logger.info(f"Executing git clone command: {' '.join(clone_cmd)}")
        
        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        logger.info(f"Git clone completed with return code: {result.returncode}")
        logger.info(f"Git clone stdout type: {type(result.stdout)}, content: {result.stdout[:200] if result.stdout else 'None'}")
        logger.info(f"Git clone stderr type: {type(result.stderr)}, content: {result.stderr[:200] if result.stderr else 'None'}")
        
        if result.returncode != 0:
            stderr_text = safe_decode_output(result.stderr)
            error_result = {
                "success": False,
                "error": f"Git clone failed: {stderr_text}",
                "repo_url": str(repo_url),
                "local_path": str(local_path),
                "git_output": stderr_text
            }
            logger.error(f"Git clone failed with result: {error_result}")
            return ensure_json_serializable(error_result)
        
        # Verify the repository was cloned successfully
        logger.info(f"Verifying repository clone at: {local_path}")
        if not local_path.exists() or not (local_path / '.git').exists():
            error_result = {
                "success": False,
                "error": "Repository cloned but .git directory not found",
                "repo_url": str(repo_url),
                "local_path": str(local_path)
            }
            logger.error(f"Repository verification failed: {error_result}")
            return ensure_json_serializable(error_result)
        
        logger.info("Repository clone verified successfully")
        
        # Extract repository metadata
        logger.info("Starting metadata extraction")
        metadata = get_repo_metadata(str(local_path))
        logger.info(f"Metadata extraction completed: {type(metadata)}")
        
        success_result = {
            "success": True,
            "repo_url": str(repo_url),
            "local_path": str(local_path),
            "repo_name": str(repo_name),
            "git_output": safe_decode_output(result.stdout),
            "metadata": metadata
        }
        logger.info(f"Clone operation completed successfully: {success_result}")
        return ensure_json_serializable(success_result)
        
    except subprocess.TimeoutExpired as e:
        timeout_result = {
            "success": False,
            "error": "Git clone operation timed out (5 minutes)",
            "repo_url": str(repo_url),
            "local_path": str(local_path) if 'local_path' in locals() else None
        }
        logger.error(f"Clone operation timed out: {timeout_result}")
        return ensure_json_serializable(timeout_result)
    except Exception as e:
        exception_result = {
            "success": False,
            "error": f"Unexpected error during clone operation: {str(e)}",
            "repo_url": str(repo_url),
            "local_path": str(local_path) if 'local_path' in locals() else None
        }
        logger.error(f"Unexpected error in clone_repo: {exception_result}", exc_info=True)
        return ensure_json_serializable(exception_result)


def get_repo_metadata(repo_path: str) -> Dict[str, Any]:
    """
    Extract metadata from a cloned git repository.
    
    Args:
        repo_path (str): Path to the cloned repository
    
    Returns:
        Dict[str, Any]: Repository metadata
    """
    logger.info(f"Starting get_repo_metadata for path: {repo_path}")
    metadata = {}
    
    try:
        # Change to repository directory
        original_cwd = os.getcwd()
        logger.info(f"Changed directory from {original_cwd} to {repo_path}")
        os.chdir(repo_path)
        
        # Get current commit hash
        logger.info("Getting commit hash")
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True
        )
        logger.info(f"Commit command result - returncode: {commit_result.returncode}, stdout type: {type(commit_result.stdout)}")
        if commit_result.returncode == 0:
            commit_hash = safe_decode_output(commit_result.stdout).strip()
            metadata["commit_hash"] = commit_hash
            logger.info(f"Commit hash extracted: {commit_hash}")
        
        # Get current branch
        logger.info("Getting current branch")
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True
        )
        logger.info(f"Branch command result - returncode: {branch_result.returncode}, stdout type: {type(branch_result.stdout)}")
        if branch_result.returncode == 0:
            current_branch = safe_decode_output(branch_result.stdout).strip()
            metadata["current_branch"] = current_branch
            logger.info(f"Current branch extracted: {current_branch}")
        
        # Get remote URL
        logger.info("Getting remote URL")
        remote_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True
        )
        logger.info(f"Remote command result - returncode: {remote_result.returncode}, stdout type: {type(remote_result.stdout)}")
        if remote_result.returncode == 0:
            remote_url = safe_decode_output(remote_result.stdout).strip()
            metadata["remote_url"] = remote_url
            logger.info(f"Remote URL extracted: {remote_url}")
        
        # Count files and directories (use current directory since we changed to repo_path)
        logger.info("Counting files and directories")
        file_count = 0
        dir_count = 0
        current_dir = "."  # We're now inside the repo directory
        for root, dirs, files in os.walk(current_dir):
            # Skip .git directory
            if '.git' in root:
                continue
            # Count files in current directory
            file_count += len(files)
            # Count directories in current directory (but filter out .git if present)
            filtered_dirs = [d for d in dirs if d != '.git']
            dir_count += len(filtered_dirs)
        
        metadata["file_count"] = int(file_count)  # Ensure int conversion
        metadata["directory_count"] = int(dir_count)  # Ensure int conversion
        logger.info(f"File count: {file_count}, Directory count: {dir_count}")
        
        # Get repository size (use current directory since we changed to repo_path)
        logger.info("Calculating repository size")
        total_size = 0
        for root, dirs, files in os.walk(current_dir):
            # Skip .git directory for size calculation too
            if '.git' in root:
                continue
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, IOError):
                    continue
        
        metadata["total_size_bytes"] = int(total_size)  # Ensure int conversion
        logger.info(f"Total repository size: {total_size} bytes")
        
    except Exception as e:
        error_msg = f"Failed to extract metadata: {str(e)}"
        metadata["error"] = error_msg
        logger.error(f"Error in get_repo_metadata: {error_msg}", exc_info=True)
    finally:
        # Return to original directory
        if 'original_cwd' in locals():
            os.chdir(original_cwd)
            logger.info(f"Returned to original directory: {original_cwd}")
    
    logger.info(f"Metadata extraction completed: {metadata}")
    return ensure_json_serializable(metadata)


def get_build_tool_info(repo_path: str) -> Dict[str, Any]:
    """
    Detect build tools and project structure in the cloned repository.
    
    Args:
        repo_path (str): Path to the cloned repository
    
    Returns:
        Dict[str, Any]: Build tool and project information
    """
    logger.info(f"Starting get_build_tool_info for path: {repo_path}")
    
    build_info = {
        "build_tool": "unknown",
        "project_type": "unknown",
        "build_files": [],
        "modules": [],
        "languages": []
    }
    
    try:
        repo_path = Path(repo_path)
        logger.info(f"Repository path converted to Path object: {repo_path}")
        
        # Check for various build tools
        build_indicators = {
            "maven": ["pom.xml"],
            "gradle": ["build.gradle", "build.gradle.kts", "gradlew", "gradlew.bat"],
            "npm": ["package.json"],
            "python": ["setup.py", "pyproject.toml", "requirements.txt", "Pipfile"],
            "make": ["Makefile", "makefile"],
            "cmake": ["CMakeLists.txt"]
        }
        
        detected_tools = []
        found_files = []
        
        # Search for build files
        logger.info("Searching for build tool indicator files")
        for tool, files in build_indicators.items():
            for file_pattern in files:
                matches = list(repo_path.rglob(file_pattern))
                if matches:
                    logger.info(f"Found {tool} build files: {[str(m) for m in matches]}")
                    detected_tools.append(tool)
                    found_files.extend([str(match.relative_to(repo_path)) for match in matches])
        
        if detected_tools:
            build_info["build_tool"] = str(detected_tools[0])  # Primary build tool - ensure string
            build_info["project_type"] = str(detected_tools[0])  # Ensure string
            logger.info(f"Detected build tool: {detected_tools[0]}")
        
        build_info["build_files"] = [str(f) for f in found_files]  # Ensure all strings
        logger.info(f"Build files found: {build_info['build_files']}")
        
        # Detect programming languages by file extensions
        language_extensions = {
            ".java": "java",
            ".js": "javascript",
            ".ts": "typescript",
            ".py": "python",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala"
        }
        
        logger.info("Detecting programming languages")
        detected_languages = set()
        for file_path in repo_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in language_extensions:
                detected_languages.add(language_extensions[file_path.suffix])
        
        build_info["languages"] = [str(lang) for lang in detected_languages]  # Ensure all strings
        logger.info(f"Detected languages: {build_info['languages']}")
        
        # Identify modules/submodules (directories with build files)
        logger.info("Identifying project modules")
        modules = []
        for tool_files in build_indicators.values():
            for file_pattern in tool_files:
                for match in repo_path.rglob(file_pattern):
                    module_dir = str(match.parent.relative_to(repo_path))
                    if module_dir != "." and module_dir not in modules:
                        modules.append(module_dir)
        
        build_info["modules"] = [str(m) for m in (modules if modules else ["."])]  # Ensure all strings
        logger.info(f"Identified modules: {build_info['modules']}")
        
    except Exception as e:
        error_msg = f"Failed to analyze build tools: {str(e)}"
        build_info["error"] = error_msg
        logger.error(f"Error in get_build_tool_info: {error_msg}", exc_info=True)
    
    logger.info(f"Build tool analysis completed: {build_info}")
    return ensure_json_serializable(build_info)


def create_repo_snapshot(clone_result: Dict[str, Any], build_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a comprehensive repository snapshot with all metadata.
    
    Args:
        clone_result (Dict[str, Any]): Result from clone_repo function
        build_info (Dict[str, Any]): Result from get_build_tool_info function
    
    Returns:
        Dict[str, Any]: Complete repository snapshot
    """
    from datetime import datetime
    
    logger.info("Starting create_repo_snapshot")
    logger.info(f"Clone result type: {type(clone_result)}, keys: {clone_result.keys() if isinstance(clone_result, dict) else 'Not a dict'}")
    logger.info(f"Build info type: {type(build_info)}, keys: {build_info.keys() if isinstance(build_info, dict) else 'Not a dict'}")
    
    snapshot = {
        "repo_id": str(uuid.uuid4()),
        "snapshot_id": str(uuid.uuid4()),
        "ingestion_timestamp": str(datetime.now().isoformat()),  # Ensure string
        "repo_url": str(clone_result.get("repo_url", "")),  # Ensure string
        "local_path": str(clone_result.get("local_path", "")),  # Ensure string
        "success": bool(clone_result.get("success", False))  # Ensure boolean
    }
    logger.info(f"Basic snapshot created: {snapshot}")
    
    if clone_result.get("success") and "metadata" in clone_result:
        logger.info("Adding metadata from clone result")
        metadata = clone_result["metadata"]
        logger.info(f"Metadata type: {type(metadata)}, content: {metadata}")
        
        snapshot.update({
            "commit": str(metadata.get("commit_hash", "")),  # Ensure string
            "branch": str(metadata.get("current_branch", "")),  # Ensure string
            "file_count": int(metadata.get("file_count", 0)),  # Ensure int
            "directory_count": int(metadata.get("directory_count", 0)),  # Ensure int
            "total_size_bytes": int(metadata.get("total_size_bytes", 0))  # Ensure int
        })
        logger.info("Metadata added to snapshot")
    
    # Add build tool information
    logger.info("Adding build tool information")
    snapshot.update({
        "build_tool": str(build_info.get("build_tool", "unknown")),  # Ensure string
        "project_type": str(build_info.get("project_type", "unknown")),  # Ensure string
        "modules": [str(m) for m in build_info.get("modules", [])],  # Ensure string list
        "languages": [str(l) for l in build_info.get("languages", [])],  # Ensure string list
        "build_files": [str(f) for f in build_info.get("build_files", [])]  # Ensure string list
    })
    logger.info("Build tool information added to snapshot")
    
    # Add notes for any errors or warnings
    logger.info("Adding notes and error information")
    notes = []
    if not clone_result.get("success"):
        notes.append(f"Clone failed: {str(clone_result.get('error', ''))}")
    
    if "error" in build_info:
        notes.append(f"Build analysis error: {str(build_info['error'])}")
    
    snapshot["notes"] = str("; ".join(notes) if notes else "Repository ingested successfully")  # Ensure string
    
    logger.info(f"Final snapshot created: {snapshot}")
    
    return ensure_json_serializable(snapshot)


# Example usage function
def ingest_repository(repo_url: str, output_dir: str = "./output") -> Dict[str, Any]:
    """
    Complete repository ingestion pipeline.
    
    Args:
        repo_url (str): GitHub repository URL
        output_dir (str): Output directory for cloning
    
    Returns:
        Dict[str, Any]: Complete ingestion results
    """
    logger.info(f"Starting complete ingestion pipeline for: {repo_url}")
    
    # Step 1: Clone repository
    logger.info("Step 1: Cloning repository")
    clone_result = clone_repo(repo_url, output_dir)
    
    if not clone_result.get("success"):
        logger.error(f"Clone failed, returning early: {clone_result}")
        return clone_result
    
    logger.info("Clone successful, proceeding to build analysis")
    
    # Step 2: Analyze build tools
    logger.info("Step 2: Analyzing build tools")
    build_info = get_build_tool_info(clone_result["local_path"])
    
    # Step 3: Create snapshot
    logger.info("Step 3: Creating repository snapshot")
    snapshot = create_repo_snapshot(clone_result, build_info)
    
    logger.info(f"Ingestion pipeline completed successfully")
    return ensure_json_serializable(snapshot)
