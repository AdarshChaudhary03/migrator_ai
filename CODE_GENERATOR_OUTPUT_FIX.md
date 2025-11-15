# Code Generator Output Location Fix

## Problem Identified

The code generator agent was successfully creating Quarkus projects, but they were being written to temporary directories (like `/tmp/quarkus-migrated-spring-boot-hello-world-a254993`) that are not easily accessible to users and get cleaned up automatically.

## Root Cause

The `create_project_structure` function was using the target path directly from the AST transformer output, which uses temporary directories for intermediate processing.

## Solution Implemented

### 1. Created Persistent Output Path Function

**File:** `agents/code_generator/code_generation_tools.py`

Added `_get_persistent_output_path()` function that:

- Converts temporary paths to persistent paths in `./output` directory
- Extracts project name from repository name or original path
- Adds timestamp to ensure unique project names
- Creates accessible output location for users

### 2. Updated Project Structure Creation

**Modified:** `create_project_structure()` function

- Added `repo_name` parameter for better project naming
- Automatically converts temporary paths to persistent output paths
- Creates projects in `./output` directory of the migration system
- Returns both original target path and persistent path for reference

### 3. Updated Agent Instructions

**File:** `agents/code_generator/instructions.txt`

- Added guidance on extracting repository name from repo_url
- Updated workflow to use persistent output locations
- Clarified that temporary paths are automatically converted
- Emphasized importance of accessible output for users

### 4. Fixed Model Configuration

**File:** `agents/code_generator/agent.py`

- Updated to use `get_llm_model()` instead of hardcoded "gemini-2.0-flash"
- Ensures consistent environment-based model configuration

## Key Changes Made

### Before (Problematic):

```python
def create_project_structure(target_path: str):
    target = Path(target_path)  # Uses temporary path directly
    # Creates project in /tmp/... (not accessible)
```

### After (Fixed):

```python
def create_project_structure(target_path: str, repo_name: str = ""):
    persistent_path = _get_persistent_output_path(target_path, repo_name)
    target = Path(persistent_path)  # Uses persistent output path
    # Creates project in ./output/... (accessible)
```

## Verification Results

✅ **Test Passed**: Complete code generation workflow successfully creates:

- Project structure in `./output/quarkus-{repo-name}_{timestamp}/`
- Java source files with proper Quarkus annotations
- Maven pom.xml with Quarkus dependencies
- Configuration files (application.properties)
- Documentation (README.md)
- All files are accessible in the output directory

✅ **Path Conversion**: Temporary paths like `/tmp/quarkus-migrated-spring-boot-hello-world-a254993` are automatically converted to persistent paths like `./output/quarkus-spring-boot-hello-world_20251115_171126/`

## Example Generated Project Structure

```
./output/quarkus-spring-boot-hello-world_20251115_171126/
├── pom.xml                                    # Quarkus Maven config
├── README.md                                  # Migration documentation
├── src/
│   ├── main/
│   │   ├── java/com/example/demo/
│   │   │   └── HelloController.java           # Converted JAX-RS controller
│   │   └── resources/
│   │       └── application.properties         # Quarkus configuration
│   └── test/
│       ├── java/                              # Test structure
│       └── resources/
└── target/                                    # Build output directory
```

## Status: RESOLVED ✅

The code generator agent now creates functional Quarkus projects in accessible locations. Users will find their migrated projects in the `./output` directory with proper naming and complete project structure.

## Next Steps for Users

After migration completes, users can:

1. Navigate to the generated project in `./output/quarkus-{project-name}_{timestamp}/`
2. Run `mvn compile` to verify the project builds
3. Start development server with `mvn quarkus:dev`
4. Begin development on their migrated Quarkus application
