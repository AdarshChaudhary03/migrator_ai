"""
Build script conversion tools for Spring Boot to Quarkus migration.
Converts Maven pom.xml and Gradle build.gradle to Quarkus-compatible configurations.
"""

import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from utils.subprocess_utils import ensure_json_serializable

logger = logging.getLogger(__name__)

@dataclass
class QuarkusExtension:
    """Represents a Quarkus extension dependency."""
    group_id: str
    artifact_id: str
    version: Optional[str] = None
    scope: str = "compile"
    description: str = ""

@dataclass
class BuildProfile:
    """Represents a build profile configuration."""
    name: str
    properties: Dict[str, str]
    dependencies: List[QuarkusExtension]
    build_config: Dict[str, Any]

@dataclass
class BuildPatch:
    """Represents a build file transformation patch."""
    file_path: str
    original_content: str
    transformed_content: str
    changes_summary: List[str]
    quarkus_extensions_added: List[QuarkusExtension]
    profiles_converted: List[BuildProfile]
    native_config_added: bool

# Current Quarkus version for build files
QUARKUS_VERSION = "3.15.1"
QUARKUS_PLATFORM_VERSION = "3.15.1"

# Quarkus BOM coordinates
QUARKUS_BOM = {
    "group_id": "io.quarkus.platform",
    "artifact_id": "quarkus-bom",
    "version": QUARKUS_PLATFORM_VERSION
}

# Quarkus Maven plugin coordinates
QUARKUS_MAVEN_PLUGIN = {
    "group_id": "io.quarkus.platform",
    "artifact_id": "quarkus-maven-plugin", 
    "version": QUARKUS_VERSION
}

# Essential Quarkus extensions for basic functionality
ESSENTIAL_QUARKUS_EXTENSIONS = [
    QuarkusExtension(
        group_id="io.quarkus",
        artifact_id="quarkus-arc",
        description="Contexts and Dependency Injection"
    ),
    QuarkusExtension(
        group_id="io.quarkus", 
        artifact_id="quarkus-resteasy-reactive",
        description="RESTEasy Reactive"
    ),
    QuarkusExtension(
        group_id="io.quarkus",
        artifact_id="quarkus-resteasy-reactive-jackson",
        description="RESTEasy Reactive with Jackson"
    )
]

def convert_build_scripts_to_quarkus(dependency_mapper_output: Dict[str, Any],
                                   config_mapper_output: Optional[Dict[str, Any]] = None,
                                   scanner_analyzer_output: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convert Maven pom.xml or Gradle build.gradle to Quarkus-compatible build configuration.
    
    Args:
        dependency_mapper_output: Dependency mapping results with Spring to Quarkus conversions
        config_mapper_output: Configuration mapping results (optional)
        scanner_analyzer_output: Spring Boot analysis results (optional)
        
    Returns:
        BuildPlan JSON with modified build files and required Quarkus extensions
    """
    try:
        build_plan = {
            "success": True,
            "conversion_timestamp": __import__("datetime").datetime.now().isoformat(),
            "source_analysis": {
                "repo_path": dependency_mapper_output.get("source_analysis", {}).get("repo_path", ""),
                "build_system": "unknown"
            },
            "build_patches": [],
            "quarkus_extensions": [],
            "build_profiles": [],
            "native_config": {},
            "conversion_summary": {
                "build_files_processed": 0,
                "extensions_added": 0,
                "profiles_converted": 0,
                "native_support_enabled": False
            },
            "migration_notes": []
        }
        
        repo_path = Path(dependency_mapper_output.get("source_analysis", {}).get("repo_path", ""))
        if not repo_path.exists():
            return {
                "success": False,
                "error": f"Repository path does not exist: {repo_path}"
            }
        
        # Determine build system and find build files
        maven_files = list(repo_path.glob("**/pom.xml"))
        gradle_files = list(repo_path.glob("**/build.gradle")) + list(repo_path.glob("**/build.gradle.kts"))
        
        if maven_files:
            build_plan["source_analysis"]["build_system"] = "maven"
            for pom_file in maven_files:
                patch = _convert_maven_pom_to_quarkus(pom_file, dependency_mapper_output, repo_path)
                if patch:
                    build_plan["build_patches"].append(_patch_to_dict(patch))
                    build_plan["conversion_summary"]["build_files_processed"] += 1
        
        elif gradle_files:
            build_plan["source_analysis"]["build_system"] = "gradle"
            for gradle_file in gradle_files:
                patch = _convert_gradle_build_to_quarkus(gradle_file, dependency_mapper_output, repo_path)
                if patch:
                    build_plan["build_patches"].append(_patch_to_dict(patch))
                    build_plan["conversion_summary"]["build_files_processed"] += 1
        else:
            return {
                "success": False,
                "error": "No Maven or Gradle build files found in repository"
            }
        
        # Aggregate extensions from all patches
        all_extensions = set()
        all_profiles = []
        native_enabled = False
        
        for patch_dict in build_plan["build_patches"]:
            for ext_dict in patch_dict["quarkus_extensions_added"]:
                all_extensions.add(f"{ext_dict['group_id']}:{ext_dict['artifact_id']}")
            all_profiles.extend(patch_dict["profiles_converted"])
            if patch_dict["native_config_added"]:
                native_enabled = True
        
        # Convert extensions back to list format for JSON
        all_extensions_list = []
        for patch_dict in build_plan["build_patches"]:
            for ext_dict in patch_dict.get("quarkus_extensions_added", []):
                all_extensions_list.append(ext_dict)
        build_plan["quarkus_extensions"] = all_extensions_list
        
        # Convert profiles back to list format for JSON  
        all_profiles_list = []
        for patch_dict in build_plan["build_patches"]:
            for profile_dict in patch_dict.get("profiles_converted", []):
                all_profiles_list.append(profile_dict)
        build_plan["build_profiles"] = all_profiles_list
        
        # Update summary
        build_plan["conversion_summary"]["extensions_added"] = len(all_extensions)
        build_plan["conversion_summary"]["profiles_converted"] = len(all_profiles)
        build_plan["conversion_summary"]["native_support_enabled"] = native_enabled
        
        # Add native configuration if requested or if complex project
        if _should_add_native_config(dependency_mapper_output, scanner_analyzer_output):
            build_plan["native_config"] = _generate_native_config()
            build_plan["conversion_summary"]["native_support_enabled"] = True
        
        # Add general recommendations
        build_plan["general_recommendations"] = _get_build_conversion_recommendations(build_plan)
        
        return ensure_json_serializable(build_plan)
        
    except Exception as e:
        logger.error(f"Error in build script conversion: {e}")
        return ensure_json_serializable({
            "success": False,
            "error": str(e),
            "message": "Failed to convert build scripts"
        })

def _convert_maven_pom_to_quarkus(pom_file: Path, dependency_output: Dict, repo_path: Path) -> Optional[BuildPatch]:
    """Convert Maven pom.xml to Quarkus configuration."""
    if not pom_file.exists():
        return None
    
    try:
        original_content = pom_file.read_text(encoding='utf-8')
        tree = ET.parse(pom_file)
        root = tree.getroot()
        
        # Define namespace
        namespace = {'maven': 'http://maven.apache.org/POM/4.0.0'}
        
        changes_summary = []
        extensions_added = []
        profiles_converted = []
        
        # 1. Update or add Quarkus BOM in dependencyManagement
        _add_quarkus_bom_to_pom(root, namespace, changes_summary)
        
        # 2. Convert Spring Boot dependencies to Quarkus extensions
        _convert_dependencies_in_pom(root, namespace, dependency_output, extensions_added, changes_summary)
        
        # 3. Add/Update Quarkus Maven plugin
        _add_quarkus_maven_plugin(root, namespace, changes_summary)
        
        # 4. Convert Maven profiles
        profiles_converted = _convert_maven_profiles(root, namespace, changes_summary)
        
        # 5. Update properties for Quarkus
        _update_maven_properties(root, namespace, changes_summary)
        
        # 6. Add native profile if needed
        native_added = _add_native_profile_to_pom(root, namespace, changes_summary)
        
        # Generate transformed content
        transformed_content = _prettify_xml(root)
        
        relative_path = str(pom_file.relative_to(repo_path))
        
        return BuildPatch(
            file_path=relative_path,
            original_content=original_content,
            transformed_content=transformed_content,
            changes_summary=changes_summary,
            quarkus_extensions_added=extensions_added,
            profiles_converted=profiles_converted,
            native_config_added=native_added
        )
        
    except Exception as e:
        logger.error(f"Error converting Maven POM {pom_file}: {e}")
        return None

def _convert_gradle_build_to_quarkus(gradle_file: Path, dependency_output: Dict, repo_path: Path) -> Optional[BuildPatch]:
    """Convert Gradle build.gradle to Quarkus configuration."""
    if not gradle_file.exists():
        return None
    
    try:
        original_content = gradle_file.read_text(encoding='utf-8')
        lines = original_content.split('\n')
        
        changes_summary = []
        extensions_added = []
        profiles_converted = []
        
        # Process Gradle build file
        transformed_lines = []
        plugins_section_found = False
        dependencies_section_found = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 1. Add Quarkus plugin
            if 'plugins {' in line or 'plugins{' in line:
                plugins_section_found = True
                transformed_lines.append(line)
                
                # Add Quarkus plugin if not present
                if not any('io.quarkus' in l for l in lines[i:i+10]):
                    transformed_lines.append(f"    id 'io.quarkus' version '{QUARKUS_VERSION}'")
                    changes_summary.append("Added Quarkus Gradle plugin")
            
            # 2. Convert dependencies
            elif 'dependencies {' in line or 'dependencies{' in line:
                dependencies_section_found = True
                transformed_lines.append(line)
                
                # Add Quarkus platform BOM
                if not any('quarkus-bom' in l for l in lines[i:i+20]):
                    transformed_lines.append(f"    implementation enforcedPlatform('io.quarkus.platform:quarkus-bom:{QUARKUS_PLATFORM_VERSION}')")
                    changes_summary.append("Added Quarkus BOM")
                
                # Process dependencies based on dependency mapping
                _convert_gradle_dependencies(lines, i, transformed_lines, dependency_output, extensions_added, changes_summary)
                
                # Skip to end of dependencies block
                while i < len(lines) and '}' not in lines[i]:
                    i += 1
                if i < len(lines):
                    transformed_lines.append(lines[i])  # Add closing brace
            else:
                transformed_lines.append(line)
            
            i += 1
        
        # Add plugins section if not found
        if not plugins_section_found:
            plugin_section = [
                "plugins {",
                f"    id 'io.quarkus' version '{QUARKUS_VERSION}'",
                "    id 'java'",
                "}"
            ]
            transformed_lines = plugin_section + [""] + transformed_lines
            changes_summary.append("Added plugins section with Quarkus plugin")
        
        # Add Quarkus tasks and configuration
        _add_quarkus_gradle_config(transformed_lines, changes_summary)
        
        transformed_content = '\n'.join(transformed_lines)
        relative_path = str(gradle_file.relative_to(repo_path))
        
        return BuildPatch(
            file_path=relative_path,
            original_content=original_content,
            transformed_content=transformed_content,
            changes_summary=changes_summary,
            quarkus_extensions_added=extensions_added,
            profiles_converted=profiles_converted,
            native_config_added=True  # Gradle native support is built-in with Quarkus plugin
        )
        
    except Exception as e:
        logger.error(f"Error converting Gradle build {gradle_file}: {e}")
        return None

def _add_quarkus_bom_to_pom(root: ET.Element, namespace: dict, changes_summary: List[str]) -> None:
    """Add Quarkus BOM to Maven dependencyManagement section."""
    
    # Find or create dependencyManagement section
    dep_mgmt = root.find('.//maven:dependencyManagement', namespace)
    if dep_mgmt is None:
        dep_mgmt = ET.SubElement(root, 'dependencyManagement')
        changes_summary.append("Added dependencyManagement section")
    
    # Find or create dependencies section within dependencyManagement
    dependencies = dep_mgmt.find('maven:dependencies', namespace)
    if dependencies is None:
        dependencies = ET.SubElement(dep_mgmt, 'dependencies')
    
    # Check if Quarkus BOM already exists
    existing_bom = dependencies.find(".//maven:dependency[maven:groupId='io.quarkus.platform'][maven:artifactId='quarkus-bom']", namespace)
    if existing_bom is None:
        # Add Quarkus BOM
        bom_dep = ET.SubElement(dependencies, 'dependency')
        
        group_id = ET.SubElement(bom_dep, 'groupId')
        group_id.text = QUARKUS_BOM["group_id"]
        
        artifact_id = ET.SubElement(bom_dep, 'artifactId')
        artifact_id.text = QUARKUS_BOM["artifact_id"]
        
        version = ET.SubElement(bom_dep, 'version')
        version.text = QUARKUS_BOM["version"]
        
        type_elem = ET.SubElement(bom_dep, 'type')
        type_elem.text = 'pom'
        
        scope = ET.SubElement(bom_dep, 'scope')
        scope.text = 'import'
        
        changes_summary.append(f"Added Quarkus BOM {QUARKUS_BOM['version']}")

def _convert_dependencies_in_pom(root: ET.Element, namespace: dict, dependency_output: Dict,
                                extensions_added: List[QuarkusExtension], changes_summary: List[str]) -> None:
    """Convert Spring Boot dependencies to Quarkus extensions in Maven POM."""
    
    dependencies_section = root.find('.//maven:dependencies', namespace)
    if dependencies_section is None:
        dependencies_section = ET.SubElement(root, 'dependencies')
    
    # Get dependency actions from dependency mapper output
    dependency_actions = dependency_output.get("dependency_actions", [])
    
    # Process remove and add actions
    for action in dependency_actions:
        if action.get("action") == "remove":
            # Remove Spring Boot dependency
            spring_dep = action.get("dependency", "")
            _remove_dependency_from_pom(dependencies_section, namespace, spring_dep, changes_summary)
        
        elif action.get("action") == "add":
            # Add Quarkus extension
            quarkus_dep = action.get("dependency", "")
            extension = _create_quarkus_extension_from_name(quarkus_dep)
            if extension:
                _add_dependency_to_pom(dependencies_section, extension, changes_summary)
                extensions_added.append(extension)
    
    # Always add essential Quarkus extensions
    for essential_ext in ESSENTIAL_QUARKUS_EXTENSIONS:
        if not _dependency_exists_in_pom(dependencies_section, namespace, essential_ext.artifact_id):
            _add_dependency_to_pom(dependencies_section, essential_ext, changes_summary)
            extensions_added.append(essential_ext)

def _add_quarkus_maven_plugin(root: ET.Element, namespace: dict, changes_summary: List[str]) -> None:
    """Add Quarkus Maven plugin to build section."""
    
    # Find or create build section
    build = root.find('.//maven:build', namespace)
    if build is None:
        build = ET.SubElement(root, 'build')
    
    # Find or create plugins section
    plugins = build.find('maven:plugins', namespace)
    if plugins is None:
        plugins = ET.SubElement(build, 'plugins')
    
    # Check if Quarkus plugin already exists
    existing_plugin = plugins.find(".//maven:plugin[maven:groupId='io.quarkus.platform'][maven:artifactId='quarkus-maven-plugin']", namespace)
    if existing_plugin is None:
        # Add Quarkus Maven plugin
        plugin = ET.SubElement(plugins, 'plugin')
        
        group_id = ET.SubElement(plugin, 'groupId')
        group_id.text = QUARKUS_MAVEN_PLUGIN["group_id"]
        
        artifact_id = ET.SubElement(plugin, 'artifactId')
        artifact_id.text = QUARKUS_MAVEN_PLUGIN["artifact_id"]
        
        version = ET.SubElement(plugin, 'version')
        version.text = QUARKUS_MAVEN_PLUGIN["version"]
        
        # Add executions
        executions = ET.SubElement(plugin, 'executions')
        execution = ET.SubElement(executions, 'execution')
        
        goals = ET.SubElement(execution, 'goals')
        goal = ET.SubElement(goals, 'goal')
        goal.text = 'build'
        
        changes_summary.append(f"Added Quarkus Maven plugin {QUARKUS_MAVEN_PLUGIN['version']}")

def _convert_maven_profiles(root: ET.Element, namespace: dict, changes_summary: List[str]) -> List[BuildProfile]:
    """Convert Maven profiles for Quarkus compatibility."""
    profiles_converted = []
    
    profiles_section = root.find('.//maven:profiles', namespace)
    if profiles_section is not None:
        for profile in profiles_section.findall('maven:profile', namespace):
            profile_id_elem = profile.find('maven:id', namespace)
            if profile_id_elem is not None:
                profile_id = profile_id_elem.text
                
                # Convert known Spring Boot profiles
                if 'dev' in profile_id.lower():
                    _convert_dev_profile_to_quarkus(profile, namespace, changes_summary)
                    profiles_converted.append(BuildProfile(
                        name=profile_id,
                        properties={"quarkus.profile": "dev"},
                        dependencies=[],
                        build_config={}
                    ))
                elif 'prod' in profile_id.lower() or 'production' in profile_id.lower():
                    _convert_prod_profile_to_quarkus(profile, namespace, changes_summary)
                    profiles_converted.append(BuildProfile(
                        name=profile_id,
                        properties={"quarkus.profile": "prod"},
                        dependencies=[],
                        build_config={}
                    ))
    
    return profiles_converted

def _update_maven_properties(root: ET.Element, namespace: dict, changes_summary: List[str]) -> None:
    """Update Maven properties for Quarkus."""
    
    properties = root.find('.//maven:properties', namespace)
    if properties is None:
        properties = ET.SubElement(root, 'properties')
    
    # Set Java version properties
    maven_compiler_source = properties.find('maven:maven.compiler.source', namespace)
    if maven_compiler_source is None:
        maven_compiler_source = ET.SubElement(properties, 'maven.compiler.source')
        maven_compiler_source.text = '17'
        changes_summary.append("Set Maven compiler source to Java 17")
    
    maven_compiler_target = properties.find('maven:maven.compiler.target', namespace)
    if maven_compiler_target is None:
        maven_compiler_target = ET.SubElement(properties, 'maven.compiler.target')
        maven_compiler_target.text = '17'
        changes_summary.append("Set Maven compiler target to Java 17")
    
    # Add Quarkus properties
    quarkus_platform_version = properties.find('maven:quarkus.platform.version', namespace)
    if quarkus_platform_version is None:
        quarkus_platform_version = ET.SubElement(properties, 'quarkus.platform.version')
        quarkus_platform_version.text = QUARKUS_PLATFORM_VERSION
        changes_summary.append(f"Added Quarkus platform version {QUARKUS_PLATFORM_VERSION}")

def _add_native_profile_to_pom(root: ET.Element, namespace: dict, changes_summary: List[str]) -> bool:
    """Add native compilation profile to Maven POM."""
    
    # Find or create profiles section
    profiles = root.find('.//maven:profiles', namespace)
    if profiles is None:
        profiles = ET.SubElement(root, 'profiles')
    
    # Check if native profile already exists
    existing_native = profiles.find(".//maven:profile[maven:id='native']", namespace)
    if existing_native is not None:
        return False
    
    # Create native profile
    native_profile = ET.SubElement(profiles, 'profile')
    
    profile_id = ET.SubElement(native_profile, 'id')
    profile_id.text = 'native'
    
    # Add properties
    properties = ET.SubElement(native_profile, 'properties')
    
    skipits = ET.SubElement(properties, 'skipITs')
    skipits.text = 'false'
    
    quarkus_package_type = ET.SubElement(properties, 'quarkus.package.type')
    quarkus_package_type.text = 'native'
    
    changes_summary.append("Added native compilation profile")
    return True

def _convert_gradle_dependencies(lines: List[str], start_idx: int, transformed_lines: List[str],
                               dependency_output: Dict, extensions_added: List[QuarkusExtension],
                               changes_summary: List[str]) -> None:
    """Convert Gradle dependencies based on dependency mapping."""
    
    dependency_actions = dependency_output.get("dependency_actions", [])
    
    # Add essential Quarkus dependencies
    for essential_ext in ESSENTIAL_QUARKUS_EXTENSIONS:
        dep_line = f"    implementation '{essential_ext.group_id}:{essential_ext.artifact_id}'"
        transformed_lines.append(dep_line)
        extensions_added.append(essential_ext)
    
    # Process mapped dependencies
    for action in dependency_actions:
        if action.get("action") == "add":
            quarkus_dep = action.get("dependency", "")
            extension = _create_quarkus_extension_from_name(quarkus_dep)
            if extension:
                dep_line = f"    implementation '{extension.group_id}:{extension.artifact_id}'"
                transformed_lines.append(dep_line)
                extensions_added.append(extension)
    
    changes_summary.append("Converted Spring Boot dependencies to Quarkus extensions")

def _add_quarkus_gradle_config(transformed_lines: List[str], changes_summary: List[str]) -> None:
    """Add Quarkus-specific Gradle configuration."""
    
    gradle_config = [
        "",
        "quarkus {",
        "    # Uncomment to enable native builds",
        "    # packageType = 'native'",
        "}",
        "",
        "tasks.named('test') {",
        "    systemProperty 'java.util.logging.manager', 'org.jboss.logmanager.LogManager'",
        "}",
        "",
        "tasks.named('testNative') {",
        "    systemProperty 'java.util.logging.manager', 'org.jboss.logmanager.LogManager'",
        "}"
    ]
    
    transformed_lines.extend(gradle_config)
    changes_summary.append("Added Quarkus Gradle configuration and native support")

def _should_add_native_config(dependency_output: Dict, scanner_output: Dict = None) -> bool:
    """Determine if native configuration should be added."""
    
    # Add native config if project is not too complex
    if scanner_output:
        risk_score = scanner_output.get("overall_risk_score", 0.0)
        return risk_score < 0.7  # Only add for low-medium risk projects
    
    return True  # Default to adding native config

def _generate_native_config() -> Dict[str, Any]:
    """Generate native compilation configuration."""
    
    return {
        "enabled": True,
        "build_args": [
            "--initialize-at-build-time",
            "--report-unsupported-elements-at-runtime"
        ],
        "resources": {
            "includes": ["**/*.properties", "**/*.xml", "**/*.json"],
            "excludes": []
        },
        "reflection_config": {
            "auto_registration": True,
            "manual_entries": []
        },
        "recommendations": [
            "Test native compilation with: ./mvnw package -Pnative",
            "For Gradle: ./gradlew build -Dquarkus.package.type=native",
            "Use @RegisterForReflection for classes requiring reflection",
            "Configure native resources in application.properties"
        ]
    }

# Helper functions
def _create_quarkus_extension_from_name(extension_name: str) -> Optional[QuarkusExtension]:
    """Create QuarkusExtension from extension name."""
    
    # Map common Quarkus extension names to full coordinates
    extension_mapping = {
        "quarkus-resteasy-reactive": QuarkusExtension("io.quarkus", "quarkus-resteasy-reactive", description="RESTEasy Reactive"),
        "quarkus-hibernate-orm-panache": QuarkusExtension("io.quarkus", "quarkus-hibernate-orm-panache", description="Hibernate ORM with Panache"),
        "quarkus-jdbc-postgresql": QuarkusExtension("io.quarkus", "quarkus-jdbc-postgresql", description="PostgreSQL JDBC driver"),
        "quarkus-redis-client": QuarkusExtension("io.quarkus", "quarkus-redis-client", description="Redis client"),
        "quarkus-security": QuarkusExtension("io.quarkus", "quarkus-security", description="Security"),
        "quarkus-smallrye-health": QuarkusExtension("io.quarkus", "quarkus-smallrye-health", description="SmallRye Health"),
        "quarkus-cache": QuarkusExtension("io.quarkus", "quarkus-cache", description="Cache"),
        "quarkus-mailer": QuarkusExtension("io.quarkus", "quarkus-mailer", description="Mailer")
    }
    
    return extension_mapping.get(extension_name)

def _remove_dependency_from_pom(dependencies: ET.Element, namespace: dict, artifact_name: str, changes_summary: List[str]) -> None:
    """Remove Spring Boot dependency from Maven POM."""
    
    for dep in dependencies.findall('maven:dependency', namespace):
        artifact_id = dep.find('maven:artifactId', namespace)
        if artifact_id is not None and artifact_name in artifact_id.text:
            dependencies.remove(dep)
            changes_summary.append(f"Removed Spring Boot dependency: {artifact_name}")

def _add_dependency_to_pom(dependencies: ET.Element, extension: QuarkusExtension, changes_summary: List[str]) -> None:
    """Add Quarkus dependency to Maven POM."""
    
    dep = ET.SubElement(dependencies, 'dependency')
    
    group_id = ET.SubElement(dep, 'groupId')
    group_id.text = extension.group_id
    
    artifact_id = ET.SubElement(dep, 'artifactId')
    artifact_id.text = extension.artifact_id
    
    # Don't add version for Quarkus extensions (managed by BOM)
    
    changes_summary.append(f"Added Quarkus extension: {extension.artifact_id}")

def _dependency_exists_in_pom(dependencies: ET.Element, namespace: dict, artifact_id: str) -> bool:
    """Check if dependency already exists in POM."""
    
    return dependencies.find(f".//maven:dependency[maven:artifactId='{artifact_id}']", namespace) is not None

def _convert_dev_profile_to_quarkus(profile: ET.Element, namespace: dict, changes_summary: List[str]) -> None:
    """Convert development profile for Quarkus."""
    
    properties = profile.find('maven:properties', namespace)
    if properties is None:
        properties = ET.SubElement(profile, 'properties')
    
    # Add Quarkus dev mode properties
    quarkus_dev = ET.SubElement(properties, 'quarkus.live-reload.instrumentation')
    quarkus_dev.text = 'true'
    
    changes_summary.append("Converted dev profile for Quarkus live reload")

def _convert_prod_profile_to_quarkus(profile: ET.Element, namespace: dict, changes_summary: List[str]) -> None:
    """Convert production profile for Quarkus."""
    
    properties = profile.find('maven:properties', namespace)
    if properties is None:
        properties = ET.SubElement(profile, 'properties')
    
    # Add Quarkus production properties
    quarkus_log = ET.SubElement(properties, 'quarkus.log.level')
    quarkus_log.text = 'INFO'
    
    changes_summary.append("Converted production profile for Quarkus")

def _prettify_xml(element: ET.Element) -> str:
    """Pretty print XML element."""
    from xml.dom import minidom
    
    rough_string = ET.tostring(element, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def _patch_to_dict(patch: BuildPatch) -> Dict[str, Any]:
    """Convert BuildPatch to dictionary."""
    return {
        "file_path": patch.file_path,
        "original_content": patch.original_content,
        "transformed_content": patch.transformed_content,
        "changes_summary": patch.changes_summary,
        "quarkus_extensions_added": [_extension_to_dict(ext) for ext in patch.quarkus_extensions_added],
        "profiles_converted": [_profile_to_dict(profile) for profile in patch.profiles_converted],
        "native_config_added": patch.native_config_added
    }

def _extension_to_dict(extension: QuarkusExtension) -> Dict[str, Any]:
    """Convert QuarkusExtension to dictionary."""
    return {
        "group_id": extension.group_id,
        "artifact_id": extension.artifact_id,
        "version": extension.version,
        "scope": extension.scope,
        "description": extension.description
    }

def _profile_to_dict(profile: BuildProfile) -> Dict[str, Any]:
    """Convert BuildProfile to dictionary."""
    return {
        "name": profile.name,
        "properties": profile.properties,
        "dependencies": [_extension_to_dict(dep) for dep in profile.dependencies],
        "build_config": profile.build_config
    }

def _get_build_conversion_recommendations(build_plan: Dict) -> List[str]:
    """Generate build conversion recommendations."""
    recommendations = []
    
    build_system = build_plan["source_analysis"]["build_system"]
    files_processed = build_plan["conversion_summary"]["build_files_processed"]
    extensions_added = build_plan["conversion_summary"]["extensions_added"]
    native_enabled = build_plan["conversion_summary"]["native_support_enabled"]
    
    if files_processed > 0:
        recommendations.append(f"Successfully converted {files_processed} {build_system.upper()} build files")
    
    if extensions_added > 0:
        recommendations.append(f"Added {extensions_added} Quarkus extensions")
    
    if native_enabled:
        recommendations.append("Native compilation support has been configured")
        if build_system == "maven":
            recommendations.append("Test native build with: ./mvnw package -Pnative")
        else:
            recommendations.append("Test native build with: ./gradlew build -Dquarkus.package.type=native")
    
    # Add general recommendations
    recommendations.extend([
        f"Run Quarkus dev mode to test changes: ./{'mvnw' if build_system == 'maven' else 'gradlew'} quarkus:dev",
        "Update any custom build scripts and CI/CD pipelines for Quarkus",
        "Test all build profiles in different environments",
        "Review and update Docker configurations for Quarkus JVM and native modes",
        "Configure Quarkus extensions based on application requirements",
        "Consider using Quarkus CLI for additional project setup and extensions"
    ])
    
    return recommendations
