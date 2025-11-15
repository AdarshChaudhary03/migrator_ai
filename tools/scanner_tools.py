"""
Scanner Analyzer Tools for Spring Boot Feature Detection
Provides functionality to scan and analyze Spring Boot projects for migration planning.
"""

import os
import subprocess
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set
from dataclasses import dataclass
import logging
import sys

from utils.subprocess_utils import safe_decode_output, ensure_json_serializable

# Add utils to path for subprocess utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.subprocess_utils import safe_decode_output, ensure_json_serializable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FeaturePattern:
    """Represents a detected Spring Boot feature pattern."""
    name: str
    type: str  # starter, annotation, configuration, etc.
    locations: List[str]
    count: int
    risk_score: float
    migration_notes: str = ""

@dataclass
class ModuleAnalysis:
    """Analysis results for a single module."""
    module_name: str
    module_path: str
    features: List[FeaturePattern]
    overall_risk_score: float
    dependency_info: Dict[str, Any]
    build_tool: str

def scan_spring_boot_features(repo_path: str) -> Dict[str, Any]:
    """
    Main function to scan repository for Spring Boot features.
    
    Args:
        repo_path: Path to the repository to scan
        
    Returns:
        FeatureMap JSON with detected patterns and risk scores
    """
    logger.info(f"Starting Spring Boot feature scan for: {repo_path}")
    
    try:
        repo_path = Path(repo_path)
        
        # Identify modules in the repository
        modules = identify_modules(repo_path)
        logger.info(f"Identified {len(modules)} modules: {[m.name for m in modules]}")
        
        # Analyze each module
        module_analyses = []
        for module in modules:
            logger.info(f"Analyzing module: {module.name}")
            analysis = analyze_module(module)
            module_analyses.append(analysis)
        
        # Generate feature map
        feature_map = generate_feature_map(repo_path, module_analyses)
        
        logger.info("Spring Boot feature scan completed successfully")
        return ensure_json_serializable(feature_map)
        
    except Exception as e:
        logger.error(f"Error during feature scan: {str(e)}")
        return ensure_json_serializable({
            "success": False,
            "error": f"Feature scan failed: {str(e)}",
            "repo_path": str(repo_path),
            "modules": [],
            "overall_risk_score": 1.0
        })

def identify_modules(repo_path: Path) -> List[Path]:
    """Identify modules within the repository based on build files."""
    modules = []
    
    # Look for Maven modules (pom.xml files)
    for pom_file in repo_path.rglob("pom.xml"):
        module_dir = pom_file.parent
        modules.append(module_dir)
    
    # Look for Gradle modules (build.gradle files)  
    for gradle_file in repo_path.rglob("build.gradle*"):
        module_dir = gradle_file.parent
        if module_dir not in modules:
            modules.append(module_dir)
    
    # If no modules found, treat root as single module
    if not modules:
        modules = [repo_path]
    
    return sorted(modules)

def analyze_module(module_path: Path) -> ModuleAnalysis:
    """Analyze a single module for Spring Boot features."""
    logger.info(f"Analyzing module: {module_path}")
    
    features = []
    build_tool = detect_build_tool(module_path)
    
    # Detect dependency features
    dependency_features = scan_dependencies(module_path, build_tool)
    features.extend(dependency_features)
    
    # Scan source code for annotations and patterns
    code_features = scan_source_code(module_path)
    features.extend(code_features)
    
    # Scan configuration files
    config_features = scan_configuration_files(module_path)
    features.extend(config_features)
    
    # Calculate overall risk score
    risk_score = calculate_module_risk_score(features)
    
    return ModuleAnalysis(
        module_name=module_path.name,
        module_path=str(module_path),
        features=features,
        overall_risk_score=risk_score,
        dependency_info=get_dependency_info(module_path, build_tool),
        build_tool=build_tool
    )

def detect_build_tool(module_path: Path) -> str:
    """Detect the build tool used in the module."""
    if (module_path / "pom.xml").exists():
        return "maven"
    elif any((module_path / f"build.gradle{ext}").exists() for ext in ["", ".kts"]):
        return "gradle"
    else:
        return "unknown"

def scan_dependencies(module_path: Path, build_tool: str) -> List[FeaturePattern]:
    """Scan build files for Spring Boot starter dependencies."""
    features = []
    
    if build_tool == "maven":
        features.extend(scan_maven_dependencies(module_path))
    elif build_tool == "gradle":
        features.extend(scan_gradle_dependencies(module_path))
    
    return features

def scan_maven_dependencies(module_path: Path) -> List[FeaturePattern]:
    """Scan Maven pom.xml for Spring Boot starters and dependencies."""
    features = []
    pom_file = module_path / "pom.xml"
    
    if not pom_file.exists():
        return features
    
    try:
        tree = ET.parse(pom_file)
        root = tree.getroot()
        
        # Define namespace (Maven uses a namespace)
        namespace = {'maven': 'http://maven.apache.org/POM/4.0.0'}
        
        # Look for Spring Boot starters
        starter_patterns = {
            'spring-boot-starter-web': {'risk': 0.3, 'notes': 'Web MVC starter - needs JAX-RS conversion'},
            'spring-boot-starter-webflux': {'risk': 0.7, 'notes': 'WebFlux starter - complex reactive migration'},
            'spring-boot-starter-data-jpa': {'risk': 0.4, 'notes': 'JPA starter - consider Panache'},
            'spring-boot-starter-data-jdbc': {'risk': 0.3, 'notes': 'JDBC starter - needs conversion'},
            'spring-boot-starter-security': {'risk': 0.5, 'notes': 'Security starter - Quarkus Security needed'},
            'spring-boot-starter-actuator': {'risk': 0.4, 'notes': 'Actuator - use Quarkus Health/Metrics'},
            'spring-boot-starter-test': {'risk': 0.2, 'notes': 'Test starter - convert to @QuarkusTest'},
            'spring-boot-starter-cache': {'risk': 0.3, 'notes': 'Cache starter - use Quarkus Cache'},
        }
        
        dependencies = root.findall('.//maven:dependency', namespace)
        for dep in dependencies:
            artifact_id = dep.find('maven:artifactId', namespace)
            if artifact_id is not None:
                artifact = artifact_id.text
                if artifact in starter_patterns:
                    pattern_info = starter_patterns[artifact]
                    features.append(FeaturePattern(
                        name=artifact,
                        type="spring_starter",
                        locations=[str(pom_file)],
                        count=1,
                        risk_score=pattern_info['risk'],
                        migration_notes=pattern_info['notes']
                    ))
        
    except Exception as e:
        logger.warning(f"Error parsing Maven pom.xml: {e}")
    
    return features

def scan_gradle_dependencies(module_path: Path) -> List[FeaturePattern]:
    """Scan Gradle build files for Spring Boot starters."""
    features = []
    
    for gradle_file in ["build.gradle", "build.gradle.kts"]:
        build_file = module_path / gradle_file
        if build_file.exists():
            try:
                content = build_file.read_text()
                
                # Spring Boot starter patterns
                starter_patterns = [
                    (r'spring-boot-starter-web', 0.3, 'Web starter - convert to JAX-RS'),
                    (r'spring-boot-starter-webflux', 0.7, 'WebFlux - complex reactive migration'),
                    (r'spring-boot-starter-data-jpa', 0.4, 'JPA starter - consider Panache'),
                    (r'spring-boot-starter-security', 0.5, 'Security - use Quarkus Security'),
                    (r'spring-boot-starter-actuator', 0.4, 'Actuator - use Health/Metrics'),
                ]
                
                for pattern, risk, notes in starter_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        features.append(FeaturePattern(
                            name=pattern.replace('\\', ''),
                            type="spring_starter",
                            locations=[str(build_file)],
                            count=len(matches),
                            risk_score=risk,
                            migration_notes=notes
                        ))
                        
            except Exception as e:
                logger.warning(f"Error reading Gradle file {build_file}: {e}")
    
    return features

def scan_source_code(module_path: Path) -> List[FeaturePattern]:
    """Scan Java source code for Spring Boot annotations and patterns."""
    features = []
    
    # Find all Java files
    java_files = list(module_path.rglob("*.java"))
    
    # Spring Boot annotation patterns
    annotation_patterns = {
        '@RestController': {'risk': 0.3, 'notes': 'REST controller - convert to JAX-RS @Path'},
        '@Controller': {'risk': 0.4, 'notes': 'MVC controller - convert to JAX-RS or template'},
        '@Service': {'risk': 0.2, 'notes': 'Service class - use CDI @ApplicationScoped'},
        '@Repository': {'risk': 0.3, 'notes': 'Repository - convert to Panache or JPA'},
        '@Component': {'risk': 0.2, 'notes': 'Component - use CDI beans'},
        '@Autowired': {'risk': 0.4, 'notes': 'Field injection - use constructor injection'},
        '@ConfigurationProperties': {'risk': 0.3, 'notes': 'Config props - use @ConfigMapping'},
        '@EnableScheduling': {'risk': 0.4, 'notes': 'Scheduling - use Quarkus Scheduler'},
        '@Scheduled': {'risk': 0.3, 'notes': 'Scheduled method - use @Scheduled with Quarkus'},
        '@EnableWebFlux': {'risk': 0.8, 'notes': 'WebFlux - complex reactive migration needed'},
        '@EnableJpaRepositories': {'risk': 0.4, 'notes': 'JPA repos - use Panache repositories'},
    }
    
    for java_file in java_files:
        try:
            content = java_file.read_text(encoding='utf-8')
            
            for annotation, info in annotation_patterns.items():
                count = len(re.findall(re.escape(annotation), content))
                if count > 0:
                    # Check if we already have this pattern
                    existing = next((f for f in features if f.name == annotation), None)
                    if existing:
                        existing.count += count
                        existing.locations.append(str(java_file))
                    else:
                        features.append(FeaturePattern(
                            name=annotation,
                            type="spring_annotation", 
                            locations=[str(java_file)],
                            count=count,
                            risk_score=info['risk'],
                            migration_notes=info['notes']
                        ))
                        
        except Exception as e:
            logger.warning(f"Error reading Java file {java_file}: {e}")
    
    return features

def scan_configuration_files(module_path: Path) -> List[FeaturePattern]:
    """Scan configuration files for Spring Boot specific configurations."""
    features = []
    
    # Application properties patterns
    config_patterns = {
        'server.port': {'risk': 0.1, 'notes': 'Server port - use quarkus.http.port'},
        'spring.datasource': {'risk': 0.3, 'notes': 'Datasource config - use quarkus.datasource'},
        'spring.jpa': {'risk': 0.3, 'notes': 'JPA config - use quarkus.hibernate-orm'},
        'spring.security': {'risk': 0.5, 'notes': 'Security config - use quarkus.security'},
        'management.endpoints': {'risk': 0.3, 'notes': 'Actuator endpoints - use quarkus.management'},
        'spring.cache': {'risk': 0.2, 'notes': 'Cache config - use quarkus.cache'},
    }
    
    # Scan application.properties files
    for props_file in module_path.rglob("application*.properties"):
        try:
            content = props_file.read_text()
            
            for pattern, info in config_patterns.items():
                count = len([line for line in content.split('\n') if pattern in line])
                if count > 0:
                    features.append(FeaturePattern(
                        name=f"config.{pattern}",
                        type="spring_config",
                        locations=[str(props_file)],
                        count=count,
                        risk_score=info['risk'],
                        migration_notes=info['notes']
                    ))
                    
        except Exception as e:
            logger.warning(f"Error reading properties file {props_file}: {e}")
    
    # Scan application.yml files  
    for yml_file in module_path.rglob("application*.yml"):
        try:
            content = yml_file.read_text()
            
            for pattern, info in config_patterns.items():
                if pattern.replace('.', ':\n  ') in content or pattern in content:
                    features.append(FeaturePattern(
                        name=f"config.{pattern}",
                        type="spring_config",
                        locations=[str(yml_file)],
                        count=1,
                        risk_score=info['risk'],
                        migration_notes=info['notes']
                    ))
                    
        except Exception as e:
            logger.warning(f"Error reading YAML file {yml_file}: {e}")
    
    return features

def get_dependency_info(module_path: Path, build_tool: str) -> Dict[str, Any]:
    """Get detailed dependency information using build tools."""
    dependency_info = {"success": False, "dependencies": [], "error": None}
    
    try:
        if build_tool == "maven":
            dependency_info = get_maven_dependencies(module_path)
        elif build_tool == "gradle":
            dependency_info = get_gradle_dependencies(module_path)
            
    except Exception as e:
        dependency_info["error"] = str(e)
        logger.warning(f"Error getting dependency info: {e}")
    
    return dependency_info

def get_maven_dependencies(module_path: Path) -> Dict[str, Any]:
    """Get Maven dependencies using mvn dependency:tree."""
    try:
        result = subprocess.run(
            ["mvn", "dependency:tree", "-DoutputType=json", "-DoutputFile=deps.json"],
            cwd=module_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        deps_file = module_path / "deps.json"
        if deps_file.exists():
            deps_content = json.loads(deps_file.read_text())
            deps_file.unlink()  # Clean up
            return {"success": True, "dependencies": deps_content, "build_tool": "maven"}
        else:
            return {"success": False, "error": "Dependency tree file not generated"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_gradle_dependencies(module_path: Path) -> Dict[str, Any]:
    """Get Gradle dependencies using gradle dependencies."""
    try:
        result = subprocess.run(
            ["./gradlew", "dependencies", "--configuration", "compileClasspath"],
            cwd=module_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return {"success": True, "dependencies": safe_decode_output(result.stdout), "build_tool": "gradle"}
        else:
            return {"success": False, "error": safe_decode_output(result.stderr)}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_module_risk_score(features: List[FeaturePattern]) -> float:
    """Calculate overall risk score for a module based on detected features."""
    if not features:
        return 0.0
    
    # Weighted risk calculation
    total_weighted_risk = 0.0
    total_weight = 0.0
    
    for feature in features:
        # Weight by count and type
        weight = feature.count
        if feature.type == "spring_starter":
            weight *= 2.0  # Starters are more significant
        elif feature.type == "spring_annotation":
            weight *= 1.5  # Annotations are important
        
        total_weighted_risk += feature.risk_score * weight
        total_weight += weight
    
    return min(total_weighted_risk / total_weight if total_weight > 0 else 0.0, 1.0)

def generate_feature_map(repo_path: Path, module_analyses: List[ModuleAnalysis]) -> Dict[str, Any]:
    """Generate the final FeatureMap JSON output."""
    
    # Calculate overall repository risk
    overall_risk = sum(analysis.overall_risk_score for analysis in module_analyses) / len(module_analyses) if module_analyses else 0.0
    
    # Collect all unique features
    all_features = {}
    for analysis in module_analyses:
        for feature in analysis.features:
            key = f"{feature.type}:{feature.name}"
            if key in all_features:
                all_features[key]["count"] += feature.count
                all_features[key]["locations"].extend(feature.locations)
            else:
                all_features[key] = {
                    "name": feature.name,
                    "type": feature.type,
                    "count": feature.count,
                    "locations": feature.locations.copy(),
                    "risk_score": feature.risk_score,
                    "migration_notes": feature.migration_notes
                }
    
    # Convert module analyses to JSON format
    modules_data = []
    for analysis in module_analyses:
        module_data = {
            "module_name": analysis.module_name,
            "module_path": analysis.module_path,
            "build_tool": analysis.build_tool,
            "risk_score": analysis.overall_risk_score,
            "feature_count": len(analysis.features),
            "features": [
                {
                    "name": f.name,
                    "type": f.type,
                    "count": f.count,
                    "risk_score": f.risk_score,
                    "locations": f.locations,
                    "migration_notes": f.migration_notes
                } for f in analysis.features
            ],
            "dependency_info": analysis.dependency_info
        }
        modules_data.append(module_data)
    
    return {
        "success": True,
        "repo_path": str(repo_path),
        "scan_timestamp": __import__("datetime").datetime.now().isoformat(),
        "overall_risk_score": overall_risk,
        "total_modules": len(module_analyses),
        "total_features_found": len(all_features),
        "summary_features": list(all_features.values()),
        "modules": modules_data,
        "migration_complexity": classify_migration_complexity(overall_risk),
        "recommended_approach": get_migration_recommendations(module_analyses)
    }

def classify_migration_complexity(risk_score: float) -> str:
    """Classify migration complexity based on risk score."""
    if risk_score < 0.3:
        return "LOW"
    elif risk_score < 0.6:
        return "MEDIUM" 
    else:
        return "HIGH"

def get_migration_recommendations(module_analyses: List[ModuleAnalysis]) -> List[str]:
    """Generate migration recommendations based on analysis."""
    recommendations = []
    
    # Check for common patterns
    has_webflux = any(
        any(f.name == "spring-boot-starter-webflux" or f.name == "@EnableWebFlux" for f in analysis.features)
        for analysis in module_analyses
    )
    
    has_web_mvc = any(
        any(f.name == "spring-boot-starter-web" or f.name == "@RestController" for f in analysis.features) 
        for analysis in module_analyses
    )
    
    has_data_jpa = any(
        any(f.name == "spring-boot-starter-data-jpa" for f in analysis.features)
        for analysis in module_analyses
    )
    
    if has_webflux:
        recommendations.append("Consider Quarkus Reactive approach for WebFlux migration")
        recommendations.append("Review reactive streams usage and convert to Mutiny")
    
    if has_web_mvc:
        recommendations.append("Convert REST controllers to JAX-RS resources")
        recommendations.append("Replace @RequestMapping with JAX-RS annotations")
        
    if has_data_jpa:
        recommendations.append("Consider Panache for simplified JPA usage")
        recommendations.append("Review repository patterns and convert to Panache repositories")
    
    if not recommendations:
        recommendations.append("Standard Spring Boot to Quarkus migration approach")
    
    return recommendations
