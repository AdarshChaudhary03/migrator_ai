import os
import json
import shutil
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

def _get_persistent_output_path(original_target_path: str, repo_name: str = "") -> str:
    """
    Convert temporary paths to persistent output paths.
    
    Args:
        original_target_path: Original target path (might be temporary)
        repo_name: Optional repository name for better naming
        
    Returns:
        Persistent output path in ./output directory
    """
    # Get the current working directory (project root)
    project_root = Path.cwd()
    output_dir = project_root / "output"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Extract project name from original path or use repo_name
    if repo_name:
        project_name = f"quarkus-{repo_name}"
    else:
        original_path = Path(original_target_path)
        if "quarkus-migrated" in original_path.name:
            project_name = original_path.name
        else:
            project_name = f"quarkus-migrated-{original_path.name}"
    
    # Add timestamp to make it unique
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    final_project_name = f"{project_name}_{timestamp}"
    
    return str(output_dir / final_project_name)

def create_project_structure(target_path: str, repo_name: str = "") -> Dict[str, Any]:
    """
    Create standard Quarkus project directory structure in a persistent location.
    
    Args:
        target_path: Original target path (might be temporary)
        repo_name: Optional repository name for better naming
        
    Returns:
        Dictionary with creation status and created directories
    """
    try:
        # Convert to persistent output path
        persistent_path = _get_persistent_output_path(target_path, repo_name)
        target = Path(persistent_path)
        
        # Create main directories
        directories = [
            target / "src" / "main" / "java",
            target / "src" / "main" / "resources",
            target / "src" / "test" / "java", 
            target / "src" / "test" / "resources",
            target / "target",
            target / ".mvn" / "wrapper"
        ]
        
        created_dirs = []
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            created_dirs.append(str(directory.relative_to(target)))
        
        return {
            "status": "success",
            "directories_created": created_dirs,
            "base_path": str(target),
            "persistent_path": persistent_path,
            "original_target": target_path,
            "message": f"Created Quarkus project structure at {persistent_path}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "directories_created": [],
            "original_target": target_path
        }

def write_source_file(file_path: str, content: str, base_path: str = "") -> Dict[str, Any]:
    """
    Write a Java source file to the project structure.
    
    Args:
        file_path: Relative path of the file (e.g., "src/main/java/com/example/HelloController.java")
        content: File content to write
        base_path: Base project path (optional)
        
    Returns:
        Dictionary with write status
    """
    try:
        if base_path:
            full_path = Path(base_path) / file_path
        else:
            full_path = Path(file_path)
        
        # Create parent directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "status": "success",
            "file_path": str(full_path),
            "relative_path": file_path,
            "message": f"Successfully wrote source file: {file_path}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path
        }

def write_build_file(file_content: str, file_type: str = "pom.xml", base_path: str = "") -> Dict[str, Any]:
    """
    Write build configuration file (pom.xml or build.gradle).
    
    Args:
        file_content: Build file content
        file_type: Type of build file ("pom.xml" or "build.gradle")
        base_path: Base project path
        
    Returns:
        Dictionary with write status
    """
    try:
        if base_path:
            full_path = Path(base_path) / file_type
        else:
            full_path = Path(file_type)
        
        # Write the build file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        return {
            "status": "success",
            "file_path": str(full_path),
            "file_type": file_type,
            "message": f"Successfully wrote build file: {file_type}"
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "file_type": file_type
        }

def write_test_file(file_path: str, content: str, base_path: str = "") -> Dict[str, Any]:
    """
    Write a test file to the project test structure.
    
    Args:
        file_path: Relative path of test file (e.g., "src/test/java/com/example/HelloControllerTest.java")
        content: Test file content
        base_path: Base project path
        
    Returns:
        Dictionary with write status
    """
    try:
        if base_path:
            full_path = Path(base_path) / file_path
        else:
            full_path = Path(file_path)
        
        # Create parent directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the test file content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "status": "success",
            "file_path": str(full_path),
            "relative_path": file_path,
            "message": f"Successfully wrote test file: {file_path}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path
        }

def write_configuration_file(file_path: str, content: str, base_path: str = "") -> Dict[str, Any]:
    """
    Write configuration files like application.properties, application.yml, etc.
    
    Args:
        file_path: Relative path of config file (e.g., "src/main/resources/application.properties")
        content: Configuration file content
        base_path: Base project path
        
    Returns:
        Dictionary with write status
    """
    try:
        if base_path:
            full_path = Path(base_path) / file_path
        else:
            full_path = Path(file_path)
        
        # Create parent directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the configuration file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "status": "success",
            "file_path": str(full_path),
            "relative_path": file_path,
            "message": f"Successfully wrote configuration file: {file_path}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path
        }

def write_documentation_file(file_name: str, content: str, base_path: str = "") -> Dict[str, Any]:
    """
    Write documentation files like README.md, MIGRATION_REPORT.md, etc.
    
    Args:
        file_name: Name of documentation file (e.g., "README.md")
        content: Documentation content
        base_path: Base project path
        
    Returns:
        Dictionary with write status
    """
    try:
        if base_path:
            full_path = Path(base_path) / file_name
        else:
            full_path = Path(file_name)
        
        # Write the documentation file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "status": "success", 
            "file_path": str(full_path),
            "file_name": file_name,
            "message": f"Successfully wrote documentation file: {file_name}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "file_name": file_name
        }

def write_docker_files(base_path: str, dockerfile_content: Optional[str] = None, dockerignore_content: Optional[str] = None) -> Dict[str, Any]:
    """
    Write Docker-related files for containerization.
    
    Args:
        base_path: Base project path
        dockerfile_content: Dockerfile content (optional, uses default if not provided)
        dockerignore_content: .dockerignore content (optional, uses default if not provided)
        
    Returns:
        Dictionary with write status
    """
    try:
        target = Path(base_path)
        files_written = []
        
        # Default Dockerfile content for Quarkus
        if not dockerfile_content:
            dockerfile_content = """FROM registry.access.redhat.com/ubi8/openjdk-17:1.15

ENV LANGUAGE='en_US:en'

# Copy the application jar and lib folder
COPY target/quarkus-app/lib/ /deployments/lib/
COPY target/quarkus-app/*.jar /deployments/
COPY target/quarkus-app/app/ /deployments/app/
COPY target/quarkus-app/quarkus/ /deployments/quarkus/

EXPOSE 8080
USER 185

ENV AB_JOLOKIA_OFF=""
ENV JAVA_OPTS="-Dquarkus.http.host=0.0.0.0 -Djava.util.logging.manager=org.jboss.logmanager.LogManager"
ENV JAVA_APP_JAR="/deployments/quarkus-run.jar"
"""
        
        # Default .dockerignore content
        if not dockerignore_content:
            dockerignore_content = """target/
!target/*-runner
!target/*-runner.jar
!target/lib/*
.mvn/
mvnw
mvnw.cmd
"""
        
        # Write Dockerfile
        dockerfile_path = target / "Dockerfile"
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
        files_written.append("Dockerfile")
        
        # Write .dockerignore
        dockerignore_path = target / ".dockerignore"
        with open(dockerignore_path, 'w', encoding='utf-8') as f:
            f.write(dockerignore_content)
        files_written.append(".dockerignore")
        
        return {
            "status": "success",
            "files_written": files_written,
            "base_path": str(target),
            "message": f"Successfully wrote Docker files: {', '.join(files_written)}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "base_path": base_path
        }

def validate_project_structure(base_path: str) -> Dict[str, Any]:
    """
    Validate that the generated Quarkus project has the correct structure.
    
    Args:
        base_path: Base project path to validate
        
    Returns:
        Dictionary with validation results
    """
    try:
        target = Path(base_path)
        validation_results = {
            "structure_valid": True,
            "missing_directories": [],
            "missing_files": [],
            "found_files": [],
            "recommendations": []
        }
        
        # Check required directories
        required_dirs = [
            "src/main/java",
            "src/main/resources",
            "src/test/java"
        ]
        
        for req_dir in required_dirs:
            dir_path = target / req_dir
            if not dir_path.exists():
                validation_results["structure_valid"] = False
                validation_results["missing_directories"].append(req_dir)
        
        # Check for build file
        pom_exists = (target / "pom.xml").exists()
        gradle_exists = (target / "build.gradle").exists() or (target / "build.gradle.kts").exists()
        
        if not (pom_exists or gradle_exists):
            validation_results["structure_valid"] = False
            validation_results["missing_files"].append("Build file (pom.xml or build.gradle)")
        elif pom_exists:
            validation_results["found_files"].append("pom.xml")
        elif gradle_exists:
            validation_results["found_files"].append("build.gradle")
        
        # Check for source files
        java_files = list(target.glob("src/main/java/**/*.java"))
        if java_files:
            validation_results["found_files"].extend([str(f.relative_to(target)) for f in java_files])
        
        # Check for test files
        test_files = list(target.glob("src/test/java/**/*.java"))
        if test_files:
            validation_results["found_files"].extend([str(f.relative_to(target)) for f in test_files])
        
        # Generate recommendations
        if not validation_results["structure_valid"]:
            validation_results["recommendations"].append("Fix missing directories and files before proceeding")
        
        validation_results["recommendations"].extend([
            "Run 'mvn compile' to verify project builds correctly" if pom_exists else "Run 'gradle build' to verify project builds correctly",
            "Test application startup with 'mvn quarkus:dev'" if pom_exists else "Test application startup with 'gradle quarkusDev'",
            "Review generated files for correctness"
        ])
        
        return validation_results
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "base_path": base_path
        }
