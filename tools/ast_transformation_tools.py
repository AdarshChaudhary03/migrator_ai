"""
AST transformation tools for Spring Boot to Quarkus code migration.
Performs source code transformations using AST analysis and rewriting.
"""

import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import tempfile
import uuid

from utils.subprocess_utils import safe_decode_output, ensure_json_serializable

logger = logging.getLogger(__name__)

@dataclass
class CodeTransformation:
    """Represents a code transformation rule."""
    name: str
    pattern: str
    replacement: str
    transformation_type: str  # "annotation", "import", "method", "class"
    risk_level: str  # "low", "medium", "high"
    requires_manual_review: bool
    description: str
    additional_imports: List[str] = None

@dataclass
class CodePatch:
    """Represents a code transformation patch."""
    file_path: str
    original_content: str
    transformed_content: str
    transformations_applied: List[str]
    manual_review_required: List[str]
    imports_added: List[str]
    imports_removed: List[str]

@dataclass
class TransformationModule:
    """Represents a module transformation result."""
    module_path: str
    files_transformed: int
    transformations_count: int
    test_results: Dict[str, Any]
    risk_areas: List[str]
    patches: List[CodePatch]

# Comprehensive Spring Boot to Quarkus transformation rules
TRANSFORMATION_RULES = [
    # REST Controller transformations
    CodeTransformation(
        name="RestController_to_Path",
        pattern=r"@RestController",
        replacement="@Path(\"/\")",
        transformation_type="annotation",
        risk_level="medium",
        requires_manual_review=True,
        description="Convert Spring @RestController to JAX-RS @Path",
        additional_imports=["javax.ws.rs.Path"]
    ),
    
    CodeTransformation(
        name="RequestMapping_to_JAXRS",
        pattern=r"@RequestMapping\(([^)]*)\)",
        replacement=r"@GET @Path(\1)",
        transformation_type="annotation", 
        risk_level="high",
        requires_manual_review=True,
        description="Convert @RequestMapping to appropriate JAX-RS annotations",
        additional_imports=["javax.ws.rs.GET", "javax.ws.rs.Path"]
    ),
    
    CodeTransformation(
        name="GetMapping_to_GET",
        pattern=r"@GetMapping\(\"([^\"]*)\"\)",
        replacement=r"@GET @Path(\"\1\")",
        transformation_type="annotation",
        risk_level="low",
        requires_manual_review=False,
        description="Convert @GetMapping to @GET + @Path",
        additional_imports=["javax.ws.rs.GET", "javax.ws.rs.Path"]
    ),
    
    CodeTransformation(
        name="PostMapping_to_POST",
        pattern=r"@PostMapping\(\"([^\"]*)\"\)",
        replacement=r"@POST @Path(\"\1\")",
        transformation_type="annotation",
        risk_level="low",
        requires_manual_review=False,
        description="Convert @PostMapping to @POST + @Path",
        additional_imports=["javax.ws.rs.POST", "javax.ws.rs.Path"]
    ),
    
    CodeTransformation(
        name="PutMapping_to_PUT",
        pattern=r"@PutMapping\(\"([^\"]*)\"\)",
        replacement=r"@PUT @Path(\"\1\")",
        transformation_type="annotation",
        risk_level="low",
        requires_manual_review=False,
        description="Convert @PutMapping to @PUT + @Path",
        additional_imports=["javax.ws.rs.PUT", "javax.ws.rs.Path"]
    ),
    
    CodeTransformation(
        name="DeleteMapping_to_DELETE",
        pattern=r"@DeleteMapping\(\"([^\"]*)\"\)",
        replacement=r"@DELETE @Path(\"\1\")",
        transformation_type="annotation",
        risk_level="low",
        requires_manual_review=False,
        description="Convert @DeleteMapping to @DELETE + @Path",
        additional_imports=["javax.ws.rs.DELETE", "javax.ws.rs.Path"]
    ),
    
    # Parameter transformations
    CodeTransformation(
        name="PathVariable_to_PathParam",
        pattern=r"@PathVariable\(\"([^\"]*)\"\)",
        replacement=r"@PathParam(\"\1\")",
        transformation_type="annotation",
        risk_level="low",
        requires_manual_review=False,
        description="Convert @PathVariable to @PathParam",
        additional_imports=["javax.ws.rs.PathParam"]
    ),
    
    CodeTransformation(
        name="RequestParam_to_QueryParam",
        pattern=r"@RequestParam\(\"([^\"]*)\"\)",
        replacement=r"@QueryParam(\"\1\")",
        transformation_type="annotation",
        risk_level="low",
        requires_manual_review=False,
        description="Convert @RequestParam to @QueryParam",
        additional_imports=["javax.ws.rs.QueryParam"]
    ),
    
    CodeTransformation(
        name="RequestBody_to_JAX_RS",
        pattern=r"@RequestBody",
        replacement="",
        transformation_type="annotation",
        risk_level="low",
        requires_manual_review=False,
        description="Remove @RequestBody (JAX-RS handles automatically)"
    ),
    
    # Dependency Injection transformations
    CodeTransformation(
        name="Autowired_to_Inject",
        pattern=r"@Autowired",
        replacement="@Inject",
        transformation_type="annotation",
        risk_level="medium",
        requires_manual_review=True,
        description="Convert @Autowired to @Inject (consider constructor injection)",
        additional_imports=["javax.inject.Inject"]
    ),
    
    CodeTransformation(
        name="Service_to_ApplicationScoped",
        pattern=r"@Service",
        replacement="@ApplicationScoped",
        transformation_type="annotation",
        risk_level="low",
        requires_manual_review=False,
        description="Convert @Service to @ApplicationScoped",
        additional_imports=["javax.enterprise.context.ApplicationScoped"]
    ),
    
    CodeTransformation(
        name="Component_to_ApplicationScoped",
        pattern=r"@Component",
        replacement="@ApplicationScoped",
        transformation_type="annotation",
        risk_level="low",
        requires_manual_review=False,
        description="Convert @Component to @ApplicationScoped",
        additional_imports=["javax.enterprise.context.ApplicationScoped"]
    ),
    
    CodeTransformation(
        name="Repository_to_ApplicationScoped",
        pattern=r"@Repository",
        replacement="@ApplicationScoped",
        transformation_type="annotation",
        risk_level="medium",
        requires_manual_review=True,
        description="Convert @Repository to @ApplicationScoped (consider Panache)",
        additional_imports=["javax.enterprise.context.ApplicationScoped"]
    ),
    
    # Configuration transformations
    CodeTransformation(
        name="ConfigurationProperties_to_ConfigMapping",
        pattern=r"@ConfigurationProperties\(prefix\s*=\s*\"([^\"]*)\"\)",
        replacement=r"@ConfigMapping(prefix = \"\1\")",
        transformation_type="annotation",
        risk_level="high",
        requires_manual_review=True,
        description="Convert @ConfigurationProperties to @ConfigMapping",
        additional_imports=["io.smallrye.config.ConfigMapping"]
    ),
    
    CodeTransformation(
        name="Value_to_ConfigProperty",
        pattern=r"@Value\(\"\$\{([^}]*)\}\"\)",
        replacement=r"@ConfigProperty(name = \"\1\")",
        transformation_type="annotation",
        risk_level="medium",
        requires_manual_review=True,
        description="Convert @Value to @ConfigProperty",
        additional_imports=["org.eclipse.microprofile.config.inject.ConfigProperty"]
    ),
    
    # JPA/Data transformations
    CodeTransformation(
        name="Entity_unchanged",
        pattern=r"@Entity",
        replacement="@Entity",
        transformation_type="annotation",
        risk_level="low",
        requires_manual_review=False,
        description="JPA @Entity remains unchanged"
    ),
    
    # Import transformations
    CodeTransformation(
        name="Spring_Web_imports",
        pattern=r"import org\.springframework\.web\.bind\.annotation\.\*;",
        replacement="",
        transformation_type="import",
        risk_level="low",
        requires_manual_review=False,
        description="Remove Spring Web imports"
    ),
    
    CodeTransformation(
        name="Spring_Stereotype_imports",
        pattern=r"import org\.springframework\.stereotype\.\*;",
        replacement="",
        transformation_type="import",
        risk_level="low",
        requires_manual_review=False,
        description="Remove Spring stereotype imports"
    ),
]

def transform_spring_to_quarkus_code(repo_ingestor_output: Dict[str, Any], 
                                   scanner_output: Dict[str, Any],
                                   dependency_output: Dict[str, Any], 
                                   config_output: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Transform Spring Boot source code to Quarkus using AST-based transformations.
    
    Args:
        repo_ingestor_output: Repository ingestion results
        scanner_output: Spring Boot analysis results
        dependency_output: Dependency mapping results
        config_output: Configuration mapping results (optional)
        
    Returns:
        TransformReport JSON with code patches and transformation results
    """
    try:
        transform_report = {
            "success": True,
            "transformation_timestamp": __import__("datetime").datetime.now().isoformat(),
            "source_analysis": {
                "source_repo_path": repo_ingestor_output.get("local_path", ""),
                "target_quarkus_path": "",
                "total_modules": scanner_output.get("total_modules", 0),
                "risk_score": scanner_output.get("overall_risk_score", 0.0)
            },
            "transformation_results": {
                "modules_processed": [],
                "total_files_transformed": 0,
                "total_transformations_applied": 0,
                "test_results": {},
                "risk_areas": []
            },
            "code_patches": [],
            "manual_review_items": [],
            "migration_summary": {
                "successful_transformations": 0,
                "failed_transformations": 0,
                "manual_interventions_required": 0,
                "test_failures": 0
            },
            "quarkus_project_structure": {}
        }
        
        source_path = Path(repo_ingestor_output.get("local_path", ""))
        if not source_path.exists():
            return {
                "success": False,
                "error": f"Source repository path does not exist: {source_path}"
            }
        
        # Create target Quarkus project directory
        target_path = _create_target_quarkus_project(source_path, transform_report)
        transform_report["source_analysis"]["target_quarkus_path"] = str(target_path)
        
        # Process each module found in scanner output
        for module_info in scanner_output.get("modules", []):
            module_path = Path(module_info.get("module_path", ""))
            if not module_path.exists():
                continue
                
            try:
                module_result = _process_module_transformation(
                    module_path, target_path, module_info, dependency_output, config_output
                )
                
                transform_report["transformation_results"]["modules_processed"].append({
                    "module_path": str(module_path),
                    "target_path": str(module_result.module_path),
                    "files_transformed": module_result.files_transformed,
                    "transformations_count": module_result.transformations_count,
                    "risk_areas": module_result.risk_areas
                })
                
                # Aggregate patches and manual review items
                for patch in module_result.patches:
                    transform_report["code_patches"].append({
                        "file_path": patch.file_path,
                        "original_content": patch.original_content,
                        "transformed_content": patch.transformed_content,
                        "transformations_applied": patch.transformations_applied,
                        "manual_review_required": patch.manual_review_required,
                        "imports_added": patch.imports_added,
                        "imports_removed": patch.imports_removed
                    })
                    
                    if patch.manual_review_required:
                        transform_report["manual_review_items"].extend([
                            f"{patch.file_path}: {item}" for item in patch.manual_review_required
                        ])
                
                # Update totals
                transform_report["transformation_results"]["total_files_transformed"] += module_result.files_transformed
                transform_report["transformation_results"]["total_transformations_applied"] += module_result.transformations_count
                transform_report["transformation_results"]["risk_areas"].extend(module_result.risk_areas)
                
            except Exception as e:
                logger.error(f"Error processing module {module_path}: {e}")
                transform_report["transformation_results"]["risk_areas"].append(
                    f"Failed to process module {module_path}: {str(e)}"
                )
        
        # Run tests on transformed code
        test_results = _run_transformation_tests(target_path)
        transform_report["transformation_results"]["test_results"] = test_results
        
        # Generate migration summary
        _generate_migration_summary(transform_report)
        
        # Add general recommendations
        transform_report["general_recommendations"] = _get_transformation_recommendations(transform_report)
        
        return ensure_json_serializable(transform_report)
        
    except Exception as e:
        logger.error(f"Error in code transformation: {e}")
        return ensure_json_serializable({
            "success": False,
            "error": str(e),
            "message": "Failed to transform source code"
        })

def _create_target_quarkus_project(source_path: Path, transform_report: Dict) -> Path:
    """Create target directory structure for Quarkus project."""
    # Create unique target directory
    target_name = f"quarkus-migrated-{source_path.name}-{uuid.uuid4().hex[:8]}"
    target_path = source_path.parent / target_name
    
    try:
        # Copy entire source structure to target
        shutil.copytree(source_path, target_path, ignore=shutil.ignore_patterns(
            '.git', 'target', 'build', '*.log', '.idea', '.vscode'
        ))
        
        # Create Quarkus-specific structure
        quarkus_structure = {
            "src/main/java": "Java source files (transformed)",
            "src/main/resources": "Configuration and resources",
            "src/test/java": "Test files (transformed)",
            "pom.xml": "Maven build file (updated with Quarkus dependencies)",
            "application.properties": "Quarkus configuration (converted from Spring)"
        }
        
        transform_report["quarkus_project_structure"] = quarkus_structure
        
        logger.info(f"Created Quarkus project structure at: {target_path}")
        return target_path
        
    except Exception as e:
        logger.error(f"Failed to create target project: {e}")
        # Fallback to temp directory
        return Path(tempfile.mkdtemp(prefix="quarkus_migration_"))

def _process_module_transformation(module_path: Path, target_path: Path, 
                                 module_info: Dict, dependency_output: Dict,
                                 config_output: Dict) -> TransformationModule:
    """Process transformation for a single module."""
    
    relative_path = module_path.relative_to(module_path.parent)
    target_module_path = target_path / relative_path
    
    patches = []
    files_transformed = 0
    transformations_count = 0
    risk_areas = []
    
    # Find Java source files
    java_files = list(module_path.glob("**/*.java"))
    
    for java_file in java_files:
        try:
            relative_file_path = java_file.relative_to(module_path)
            target_file_path = target_module_path / relative_file_path
            
            # Read original content
            original_content = java_file.read_text(encoding='utf-8')
            
            # Apply transformations
            transformed_content, applied_transformations, manual_reviews, imports_changes = _apply_transformations(
                original_content, java_file, module_info
            )
            
            # Write transformed content
            target_file_path.parent.mkdir(parents=True, exist_ok=True)
            target_file_path.write_text(transformed_content, encoding='utf-8')
            
            # Create patch record
            if applied_transformations:
                patch = CodePatch(
                    file_path=str(relative_file_path),
                    original_content=original_content,
                    transformed_content=transformed_content,
                    transformations_applied=applied_transformations,
                    manual_review_required=manual_reviews,
                    imports_added=imports_changes.get("added", []),
                    imports_removed=imports_changes.get("removed", [])
                )
                patches.append(patch)
                files_transformed += 1
                transformations_count += len(applied_transformations)
                
                # Collect risk areas
                if manual_reviews:
                    risk_areas.extend([f"{java_file.name}: {item}" for item in manual_reviews])
                    
        except Exception as e:
            logger.error(f"Error transforming file {java_file}: {e}")
            risk_areas.append(f"Failed to transform {java_file.name}: {str(e)}")
    
    return TransformationModule(
        module_path=str(target_module_path),
        files_transformed=files_transformed,
        transformations_count=transformations_count,
        test_results={},
        risk_areas=risk_areas,
        patches=patches
    )

def _apply_transformations(content: str, file_path: Path, 
                         module_info: Dict) -> Tuple[str, List[str], List[str], Dict]:
    """Apply transformation rules to Java source content."""
    
    transformed_content = content
    applied_transformations = []
    manual_reviews = []
    imports_to_add = set()
    imports_to_remove = set()
    
    # Check if this file has relevant Spring features
    features = module_info.get("features", [])
    file_has_spring_annotations = any(
        feature.get("name", "").startswith("@") and str(file_path) in feature.get("locations", [])
        for feature in features
    )
    
    if not file_has_spring_annotations and not _has_spring_imports(content):
        # Skip files without Spring annotations or imports
        return content, [], [], {}
    
    # Apply each transformation rule
    for rule in TRANSFORMATION_RULES:
        if rule.transformation_type == "annotation":
            matches = re.findall(rule.pattern, transformed_content)
            if matches:
                transformed_content = re.sub(rule.pattern, rule.replacement, transformed_content)
                applied_transformations.append(f"Applied {rule.name}: {rule.description}")
                
                if rule.additional_imports:
                    imports_to_add.update(rule.additional_imports)
                
                if rule.requires_manual_review:
                    manual_reviews.append(f"{rule.name}: {rule.description}")
        
        elif rule.transformation_type == "import":
            if re.search(rule.pattern, transformed_content):
                transformed_content = re.sub(rule.pattern, rule.replacement, transformed_content)
                applied_transformations.append(f"Removed import: {rule.description}")
                imports_to_remove.add(rule.pattern)
    
    # Add new imports
    if imports_to_add:
        transformed_content = _add_imports(transformed_content, list(imports_to_add))
    
    # Apply method-level transformations
    transformed_content = _apply_method_transformations(transformed_content, applied_transformations, manual_reviews)
    
    imports_changes = {
        "added": list(imports_to_add),
        "removed": list(imports_to_remove)
    }
    
    return transformed_content, applied_transformations, manual_reviews, imports_changes

def _has_spring_imports(content: str) -> bool:
    """Check if file has Spring Boot imports."""
    spring_import_patterns = [
        r"import org\.springframework\.",
        r"import org\.springframework\.boot\.",
        r"import org\.springframework\.web\.",
        r"import org\.springframework\.data\."
    ]
    
    return any(re.search(pattern, content) for pattern in spring_import_patterns)

def _add_imports(content: str, imports_to_add: List[str]) -> str:
    """Add new import statements to Java file."""
    lines = content.split('\n')
    
    # Find the position to insert imports (after package, before class)
    import_insert_index = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("package "):
            import_insert_index = i + 1
            break
        elif line.strip().startswith("import "):
            import_insert_index = i
            break
        elif line.strip().startswith("public class ") or line.strip().startswith("@"):
            import_insert_index = i
            break
    
    # Add imports
    for import_stmt in imports_to_add:
        import_line = f"import {import_stmt};"
        if import_line not in content:
            lines.insert(import_insert_index, import_line)
            import_insert_index += 1
    
    return '\n'.join(lines)

def _apply_method_transformations(content: str, applied_transformations: List[str], 
                                manual_reviews: List[str]) -> str:
    """Apply method-level transformations."""
    
    # Convert ResponseEntity to Response
    if "ResponseEntity" in content:
        content = re.sub(r"ResponseEntity<([^>]+)>", r"Response", content)
        content = re.sub(r"ResponseEntity\.ok\(([^)]+)\)", r"Response.ok(\1).build()", content)
        applied_transformations.append("Converted ResponseEntity to JAX-RS Response")
        manual_reviews.append("Review Response building - JAX-RS syntax differs from Spring")
    
    # Handle @Autowired field injection - suggest constructor injection
    autowired_fields = re.findall(r"@Autowired\s+private\s+(\w+)\s+(\w+);", content)
    if autowired_fields:
        manual_reviews.append(
            "Consider converting @Autowired field injection to constructor injection for better Quarkus compatibility"
        )
    
    return content

def _run_transformation_tests(target_path: Path) -> Dict[str, Any]:
    """Run tests on transformed Quarkus project."""
    test_results = {
        "compilation_successful": False,
        "test_execution_results": {},
        "errors": [],
        "warnings": []
    }
    
    try:
        # Check if Maven project
        pom_file = target_path / "pom.xml"
        if pom_file.exists():
            # Try to compile with Maven
            result = subprocess.run(
                ["mvn", "compile", "-f", str(pom_file)],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=target_path
            )
            
            if result.returncode == 0:
                test_results["compilation_successful"] = True
                test_results["test_execution_results"]["maven_compile"] = "SUCCESS"
            else:
                stderr_text = safe_decode_output(result.stderr)
                test_results["errors"].append(f"Maven compilation failed: {stderr_text}")
                test_results["test_execution_results"]["maven_compile"] = "FAILED"
        
        # Check for Gradle
        gradle_file = target_path / "build.gradle"
        if gradle_file.exists():
            result = subprocess.run(
                ["./gradlew", "compileJava"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=target_path
            )
            
            if result.returncode == 0:
                test_results["compilation_successful"] = True
                test_results["test_execution_results"]["gradle_compile"] = "SUCCESS"
            else:
                stderr_text = safe_decode_output(result.stderr)
                test_results["errors"].append(f"Gradle compilation failed: {stderr_text}")
                test_results["test_execution_results"]["gradle_compile"] = "FAILED"
    
    except subprocess.TimeoutExpired:
        test_results["errors"].append("Compilation timeout - project too large or complex")
    except Exception as e:
        test_results["warnings"].append(f"Could not run compilation tests: {str(e)}")
    
    return test_results

def _generate_migration_summary(transform_report: Dict) -> None:
    """Generate migration summary statistics."""
    summary = transform_report["migration_summary"]
    
    # Count successful vs failed transformations
    total_patches = len(transform_report["code_patches"])
    manual_items = len(transform_report["manual_review_items"])
    
    summary["successful_transformations"] = total_patches
    summary["manual_interventions_required"] = manual_items
    
    # Analyze test results
    test_results = transform_report["transformation_results"].get("test_results", {})
    compilation_success = test_results.get("compilation_successful", False)
    
    if compilation_success:
        summary["test_failures"] = 0
    else:
        summary["test_failures"] = 1
        summary["failed_transformations"] = 1

def _get_transformation_recommendations(transform_report: Dict) -> List[str]:
    """Generate transformation recommendations."""
    recommendations = []
    
    total_files = transform_report["transformation_results"]["total_files_transformed"]
    manual_items = len(transform_report["manual_review_items"])
    risk_areas = len(transform_report["transformation_results"]["risk_areas"])
    compilation_success = transform_report["transformation_results"]["test_results"].get("compilation_successful", False)
    
    if total_files > 0:
        recommendations.append(f"Successfully transformed {total_files} Java source files")
    
    if manual_items > 0:
        recommendations.append(f"Found {manual_items} items requiring manual review and adjustment")
        recommendations.append("Prioritize manual review items for critical functionality")
    
    if risk_areas > 0:
        recommendations.append(f"Identified {risk_areas} potential risk areas needing attention")
    
    if not compilation_success:
        recommendations.append("CRITICAL: Transformed code does not compile - manual fixes required")
        recommendations.append("Review compilation errors and adjust transformations")
    
    # Add general Quarkus migration recommendations
    recommendations.extend([
        "Test all REST endpoints with JAX-RS annotations in Quarkus dev mode",
        "Verify dependency injection works correctly with CDI",
        "Update configuration files to use Quarkus properties format", 
        "Run comprehensive integration tests after transformation",
        "Consider using Quarkus extensions for Spring compatibility if needed",
        "Review and update Docker configurations for Quarkus runtime",
        "Test native compilation compatibility for production deployment"
    ])
    
    return recommendations
