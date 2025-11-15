"""
Dependency mapping tools for Spring Boot to Quarkus migration.
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path

from utils.subprocess_utils import ensure_json_serializable

logger = logging.getLogger(__name__)

@dataclass
class DependencyMapping:
    """Represents a dependency mapping from Spring Boot to Quarkus."""
    spring_dependency: str
    quarkus_dependencies: List[str]
    confidence: float  # 0.0 to 1.0
    migration_type: str  # "direct", "equivalent", "manual", "incompatible"
    reason: str
    additional_notes: Optional[str] = None

@dataclass
class DependencyAction:
    """Represents an action to take on a dependency."""
    action: str  # "add", "remove", "replace", "flag"
    dependency: str
    reason: str
    target_dependency: Optional[str] = None
    confidence: float = 1.0
    manual_steps: Optional[List[str]] = None

# Comprehensive Spring Boot to Quarkus dependency mapping table
DEPENDENCY_MAPPING_TABLE = {
    # Web starters
    "spring-boot-starter-web": DependencyMapping(
        spring_dependency="spring-boot-starter-web",
        quarkus_dependencies=["quarkus-resteasy-reactive", "quarkus-resteasy-reactive-jackson"],
        confidence=0.9,
        migration_type="equivalent",
        reason="Spring Boot Web MVC maps to Quarkus RESTEasy Reactive for REST endpoints",
        additional_notes="Consider quarkus-vertx-web for low-level web handling"
    ),
    
    "spring-boot-starter-webflux": DependencyMapping(
        spring_dependency="spring-boot-starter-webflux",
        quarkus_dependencies=["quarkus-vertx", "quarkus-mutiny"],
        confidence=0.7,
        migration_type="equivalent", 
        reason="WebFlux reactive programming maps to Quarkus Vert.x with Mutiny",
        additional_notes="Requires significant code changes for reactive streams"
    ),
    
    # Data starters
    "spring-boot-starter-data-jpa": DependencyMapping(
        spring_dependency="spring-boot-starter-data-jpa",
        quarkus_dependencies=["quarkus-hibernate-orm-panache", "quarkus-jdbc-postgresql"],
        confidence=0.8,
        migration_type="equivalent",
        reason="Spring Data JPA maps to Quarkus Panache for simplified JPA",
        additional_notes="Database driver needs to be specified separately"
    ),
    
    "spring-boot-starter-data-jdbc": DependencyMapping(
        spring_dependency="spring-boot-starter-data-jdbc",
        quarkus_dependencies=["quarkus-agroal", "quarkus-jdbc-postgresql"],
        confidence=0.8,
        migration_type="equivalent",
        reason="Spring Data JDBC maps to Quarkus JDBC with Agroal connection pooling"
    ),
    
    "spring-boot-starter-data-redis": DependencyMapping(
        spring_dependency="spring-boot-starter-data-redis",
        quarkus_dependencies=["quarkus-redis-client"],
        confidence=0.9,
        migration_type="direct",
        reason="Direct mapping to Quarkus Redis client"
    ),
    
    "spring-boot-starter-data-mongodb": DependencyMapping(
        spring_dependency="spring-boot-starter-data-mongodb",
        quarkus_dependencies=["quarkus-mongodb-panache", "quarkus-mongodb-client"],
        confidence=0.8,
        migration_type="equivalent",
        reason="MongoDB operations map to Quarkus MongoDB with Panache"
    ),
    
    # Security
    "spring-boot-starter-security": DependencyMapping(
        spring_dependency="spring-boot-starter-security",
        quarkus_dependencies=["quarkus-security", "quarkus-security-jpa"],
        confidence=0.6,
        migration_type="manual",
        reason="Spring Security requires manual configuration migration",
        additional_notes="Security configs need complete rewrite for Quarkus"
    ),
    
    "spring-boot-starter-oauth2-client": DependencyMapping(
        spring_dependency="spring-boot-starter-oauth2-client",
        quarkus_dependencies=["quarkus-oidc", "quarkus-oidc-client"],
        confidence=0.7,
        migration_type="equivalent",
        reason="OAuth2 client functionality maps to Quarkus OIDC"
    ),
    
    # Testing
    "spring-boot-starter-test": DependencyMapping(
        spring_dependency="spring-boot-starter-test",
        quarkus_dependencies=["quarkus-junit5", "quarkus-test-security", "io.rest-assured:rest-assured"],
        confidence=0.8,
        migration_type="equivalent",
        reason="Spring Boot Test maps to Quarkus testing framework with JUnit 5"
    ),
    
    # Messaging
    "spring-boot-starter-amqp": DependencyMapping(
        spring_dependency="spring-boot-starter-amqp",
        quarkus_dependencies=["quarkus-messaging-rabbitmq"],
        confidence=0.8,
        migration_type="equivalent",
        reason="AMQP messaging maps to Quarkus RabbitMQ connector"
    ),
    
    "spring-kafka": DependencyMapping(
        spring_dependency="spring-kafka",
        quarkus_dependencies=["quarkus-kafka-streams", "quarkus-messaging-kafka"],
        confidence=0.9,
        migration_type="direct",
        reason="Kafka integration has direct Quarkus equivalent"
    ),
    
    # Actuator and monitoring
    "spring-boot-starter-actuator": DependencyMapping(
        spring_dependency="spring-boot-starter-actuator",
        quarkus_dependencies=["quarkus-smallrye-health", "quarkus-smallrye-metrics", "quarkus-info"],
        confidence=0.8,
        migration_type="equivalent",
        reason="Actuator features map to Quarkus health, metrics, and info endpoints"
    ),
    
    # Cache
    "spring-boot-starter-cache": DependencyMapping(
        spring_dependency="spring-boot-starter-cache",
        quarkus_dependencies=["quarkus-cache"],
        confidence=0.9,
        migration_type="direct",
        reason="Direct mapping to Quarkus caching"
    ),
    
    # Validation
    "spring-boot-starter-validation": DependencyMapping(
        spring_dependency="spring-boot-starter-validation",
        quarkus_dependencies=["quarkus-hibernate-validator"],
        confidence=0.9,
        migration_type="direct",
        reason="Bean validation maps directly to Quarkus validator"
    ),
    
    # Mail
    "spring-boot-starter-mail": DependencyMapping(
        spring_dependency="spring-boot-starter-mail",
        quarkus_dependencies=["quarkus-mailer"],
        confidence=0.8,
        migration_type="equivalent",
        reason="Mail functionality maps to Quarkus mailer"
    ),
    
    # Batch processing
    "spring-batch-core": DependencyMapping(
        spring_dependency="spring-batch-core",
        quarkus_dependencies=[],
        confidence=0.0,
        migration_type="incompatible",
        reason="Spring Batch has no direct Quarkus equivalent - consider alternative approaches",
        additional_notes="Use Quarkus scheduler or external batch processing tools"
    ),
    
    # Cloud
    "spring-cloud-starter-netflix-eureka-client": DependencyMapping(
        spring_dependency="spring-cloud-starter-netflix-eureka-client",
        quarkus_dependencies=["quarkus-consul-config"],
        confidence=0.5,
        migration_type="manual",
        reason="Service discovery needs migration to Quarkus-compatible solution",
        additional_notes="Consider Consul or Kubernetes service discovery"
    ),
}

def map_spring_dependencies_to_quarkus(scanner_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Spring Boot dependencies found in scanner output to Quarkus equivalents.
    
    Args:
        scanner_output: Output from scanner_analyzer_agent containing Spring Boot analysis
        
    Returns:
        DependencyPlan JSON with add/remove/replace entries and confidence scores
    """
    try:
        dependency_plan = {
            "success": True,
            "mapping_timestamp": __import__("datetime").datetime.now().isoformat(),
            "source_analysis": {
                "repo_path": scanner_output.get("repo_path", ""),
                "total_modules": scanner_output.get("total_modules", 0),
                "overall_risk_score": scanner_output.get("overall_risk_score", 0.0)
            },
            "dependency_actions": [],
            "manual_migration_items": [],
            "incompatible_dependencies": [],
            "migration_summary": {
                "total_dependencies_analyzed": 0,
                "direct_mappings": 0,
                "equivalent_mappings": 0,
                "manual_migrations": 0,
                "incompatible_items": 0,
                "overall_confidence": 0.0
            }
        }
        
        all_actions = []
        confidence_scores = []
        
        # Process each module in the scanner output
        for module in scanner_output.get("modules", []):
            module_path = module.get("module_path", "")
            
            # Process features that represent dependencies
            for feature in module.get("features", []):
                feature_name = feature.get("name", "")
                
                # Check if this feature is a Spring dependency we can map
                if feature_name in DEPENDENCY_MAPPING_TABLE:
                    mapping = DEPENDENCY_MAPPING_TABLE[feature_name]
                    confidence_scores.append(mapping.confidence)
                    
                    # Create remove action for Spring dependency
                    remove_action = DependencyAction(
                        action="remove",
                        dependency=mapping.spring_dependency,
                        reason=f"Removing Spring Boot dependency: {mapping.reason}",
                        confidence=mapping.confidence
                    )
                    all_actions.append(remove_action)
                    
                    # Handle based on migration type
                    if mapping.migration_type == "direct" or mapping.migration_type == "equivalent":
                        # Add Quarkus dependencies
                        for quarkus_dep in mapping.quarkus_dependencies:
                            add_action = DependencyAction(
                                action="add",
                                dependency=quarkus_dep,
                                reason=f"Adding Quarkus equivalent for {mapping.spring_dependency}",
                                confidence=mapping.confidence
                            )
                            all_actions.append(add_action)
                        
                        if mapping.migration_type == "direct":
                            dependency_plan["migration_summary"]["direct_mappings"] += 1
                        else:
                            dependency_plan["migration_summary"]["equivalent_mappings"] += 1
                            
                    elif mapping.migration_type == "manual":
                        # Flag for manual migration
                        manual_item = {
                            "spring_dependency": mapping.spring_dependency,
                            "quarkus_alternatives": mapping.quarkus_dependencies,
                            "reason": mapping.reason,
                            "confidence": mapping.confidence,
                            "manual_steps": [
                                f"Review {mapping.spring_dependency} usage in {module_path}",
                                f"Implement equivalent functionality using {', '.join(mapping.quarkus_dependencies)}",
                                "Test thoroughly due to API differences"
                            ],
                            "additional_notes": mapping.additional_notes
                        }
                        dependency_plan["manual_migration_items"].append(manual_item)
                        dependency_plan["migration_summary"]["manual_migrations"] += 1
                        
                    elif mapping.migration_type == "incompatible":
                        # Flag as incompatible
                        incompatible_item = {
                            "spring_dependency": mapping.spring_dependency,
                            "reason": mapping.reason,
                            "locations": feature.get("locations", []),
                            "alternative_approaches": mapping.additional_notes,
                            "impact": "HIGH - Requires architectural changes"
                        }
                        dependency_plan["incompatible_dependencies"].append(incompatible_item)
                        dependency_plan["migration_summary"]["incompatible_items"] += 1
        
        # Convert actions to JSON format
        dependency_plan["dependency_actions"] = [
            {
                "action": action.action,
                "dependency": action.dependency,
                "target_dependency": action.target_dependency,
                "reason": action.reason,
                "confidence": action.confidence,
                "manual_steps": action.manual_steps
            }
            for action in all_actions
        ]
        
        # Calculate summary statistics
        total_analyzed = len(confidence_scores)
        dependency_plan["migration_summary"]["total_dependencies_analyzed"] = total_analyzed
        
        if confidence_scores:
            dependency_plan["migration_summary"]["overall_confidence"] = sum(confidence_scores) / len(confidence_scores)
        
        # Add general recommendations
        dependency_plan["general_recommendations"] = _get_general_recommendations(scanner_output, dependency_plan)
        
        return ensure_json_serializable(dependency_plan)
        
    except Exception as e:
        logger.error(f"Error in dependency mapping: {e}")
        return ensure_json_serializable({
            "success": False,
            "error": str(e),
            "message": "Failed to map dependencies"
        })

def _get_general_recommendations(scanner_output: Dict[str, Any], dependency_plan: Dict[str, Any]) -> List[str]:
    """Generate general recommendations based on analysis."""
    recommendations = []
    
    overall_risk = scanner_output.get("overall_risk_score", 0.0)
    incompatible_count = dependency_plan["migration_summary"]["incompatible_items"]
    manual_count = dependency_plan["migration_summary"]["manual_migrations"]
    
    if overall_risk > 0.7:
        recommendations.append("HIGH RISK: Consider phased migration approach")
        recommendations.append("Thoroughly test each component after migration")
    
    if incompatible_count > 0:
        recommendations.append(f"Found {incompatible_count} incompatible dependencies requiring architectural changes")
        recommendations.append("Plan for alternative implementations of incompatible components")
    
    if manual_count > 3:
        recommendations.append(f"Found {manual_count} dependencies requiring manual migration")
        recommendations.append("Allocate additional time for manual migration tasks")
    
    # Add Quarkus-specific recommendations
    recommendations.extend([
        "Update build configuration (Maven/Gradle) with Quarkus BOM",
        "Configure Quarkus application.properties from Spring application.yml/properties",
        "Test native compilation compatibility for all dependencies",
        "Review and update Docker configurations for Quarkus",
        "Plan for Quarkus dev mode testing and debugging"
    ])
    
    return recommendations
