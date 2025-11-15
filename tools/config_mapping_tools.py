"""
Configuration mapping tools for Spring Boot to Quarkus migration.
Converts Spring application.properties/yaml to Quarkus equivalents.
"""

import json
import logging
import re
import yaml
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from utils.subprocess_utils import ensure_json_serializable

logger = logging.getLogger(__name__)

@dataclass
class ConfigMapping:
    """Represents a configuration property mapping from Spring Boot to Quarkus."""
    spring_property: str
    quarkus_property: str
    conversion_type: str  # "direct", "transform", "manual", "deprecated"
    transformation_rule: Optional[str] = None
    migration_notes: Optional[str] = None
    requires_dependency: Optional[str] = None

@dataclass
class ConfigPatch:
    """Represents a configuration file patch with changes."""
    file_path: str
    original_content: str
    patched_content: str
    diff_summary: List[str]
    migration_notes: List[str]
    environment_variables: List[str]
    secrets_identified: List[str]

# Comprehensive Spring Boot to Quarkus configuration mapping
CONFIG_MAPPING_TABLE = {
    # Server configuration
    "server.port": ConfigMapping(
        spring_property="server.port",
        quarkus_property="quarkus.http.port",
        conversion_type="direct"
    ),
    "server.servlet.context-path": ConfigMapping(
        spring_property="server.servlet.context-path",
        quarkus_property="quarkus.http.root-path", 
        conversion_type="direct"
    ),
    "server.address": ConfigMapping(
        spring_property="server.address",
        quarkus_property="quarkus.http.host",
        conversion_type="direct"
    ),
    "server.ssl.enabled": ConfigMapping(
        spring_property="server.ssl.enabled",
        quarkus_property="quarkus.http.ssl.certificate.key-store-file",
        conversion_type="manual",
        migration_notes="SSL configuration requires manual setup in Quarkus"
    ),
    
    # Database configuration - Generic
    "spring.datasource.url": ConfigMapping(
        spring_property="spring.datasource.url",
        quarkus_property="quarkus.datasource.jdbc.url",
        conversion_type="direct"
    ),
    "spring.datasource.username": ConfigMapping(
        spring_property="spring.datasource.username", 
        quarkus_property="quarkus.datasource.username",
        conversion_type="direct"
    ),
    "spring.datasource.password": ConfigMapping(
        spring_property="spring.datasource.password",
        quarkus_property="quarkus.datasource.password",
        conversion_type="direct"
    ),
    "spring.datasource.driver-class-name": ConfigMapping(
        spring_property="spring.datasource.driver-class-name",
        quarkus_property="quarkus.datasource.jdbc.driver",
        conversion_type="direct"
    ),
    
    # JPA/Hibernate configuration
    "spring.jpa.hibernate.ddl-auto": ConfigMapping(
        spring_property="spring.jpa.hibernate.ddl-auto",
        quarkus_property="quarkus.hibernate-orm.database.generation",
        conversion_type="transform",
        transformation_rule="Map values: create->create, update->update, create-drop->drop-and-create, validate->validate, none->none"
    ),
    "spring.jpa.show-sql": ConfigMapping(
        spring_property="spring.jpa.show-sql",
        quarkus_property="quarkus.hibernate-orm.log.sql",
        conversion_type="direct"
    ),
    "spring.jpa.properties.hibernate.dialect": ConfigMapping(
        spring_property="spring.jpa.properties.hibernate.dialect",
        quarkus_property="quarkus.hibernate-orm.dialect",
        conversion_type="direct"
    ),
    "spring.jpa.properties.hibernate.format_sql": ConfigMapping(
        spring_property="spring.jpa.properties.hibernate.format_sql",
        quarkus_property="quarkus.hibernate-orm.log.format-sql",
        conversion_type="direct"
    ),
    
    # Logging configuration
    "logging.level.root": ConfigMapping(
        spring_property="logging.level.root",
        quarkus_property="quarkus.log.level",
        conversion_type="direct"
    ),
    "logging.level.org.springframework": ConfigMapping(
        spring_property="logging.level.org.springframework",
        quarkus_property="quarkus.log.category.\"org.springframework\".level",
        conversion_type="transform",
        transformation_rule="Use category-based logging configuration"
    ),
    "logging.file.name": ConfigMapping(
        spring_property="logging.file.name",
        quarkus_property="quarkus.log.file.path",
        conversion_type="direct"
    ),
    "logging.pattern.console": ConfigMapping(
        spring_property="logging.pattern.console",
        quarkus_property="quarkus.log.console.format",
        conversion_type="direct"
    ),
    
    # Redis configuration
    "spring.redis.host": ConfigMapping(
        spring_property="spring.redis.host",
        quarkus_property="quarkus.redis.hosts",
        conversion_type="transform",
        transformation_rule="Format as redis://host:port"
    ),
    "spring.redis.port": ConfigMapping(
        spring_property="spring.redis.port", 
        quarkus_property="quarkus.redis.hosts",
        conversion_type="transform",
        transformation_rule="Combine with host as redis://host:port"
    ),
    "spring.redis.password": ConfigMapping(
        spring_property="spring.redis.password",
        quarkus_property="quarkus.redis.password",
        conversion_type="direct"
    ),
    
    # Kafka configuration
    "spring.kafka.bootstrap-servers": ConfigMapping(
        spring_property="spring.kafka.bootstrap-servers",
        quarkus_property="kafka.bootstrap.servers",
        conversion_type="direct"
    ),
    "spring.kafka.consumer.group-id": ConfigMapping(
        spring_property="spring.kafka.consumer.group-id",
        quarkus_property="mp.messaging.incoming.[channel].group.id",
        conversion_type="manual",
        migration_notes="Requires channel-specific configuration in Quarkus"
    ),
    
    # Security configuration
    "spring.security.user.name": ConfigMapping(
        spring_property="spring.security.user.name",
        quarkus_property="quarkus.security.users.embedded.users.[username]",
        conversion_type="manual",
        migration_notes="Security configuration requires manual migration"
    ),
    
    # Actuator configuration
    "management.endpoints.web.exposure.include": ConfigMapping(
        spring_property="management.endpoints.web.exposure.include",
        quarkus_property="quarkus.smallrye-health.ui.always-include",
        conversion_type="manual",
        migration_notes="Map to appropriate Quarkus health/metrics endpoints"
    ),
    "management.endpoint.health.show-details": ConfigMapping(
        spring_property="management.endpoint.health.show-details",
        quarkus_property="quarkus.smallrye-health.ui.always-include",
        conversion_type="transform"
    ),
    
    # Cache configuration
    "spring.cache.type": ConfigMapping(
        spring_property="spring.cache.type",
        quarkus_property="quarkus.cache.caffeine.initial-capacity",
        conversion_type="manual",
        migration_notes="Cache configuration differs significantly in Quarkus"
    ),
    
    # Mail configuration
    "spring.mail.host": ConfigMapping(
        spring_property="spring.mail.host",
        quarkus_property="quarkus.mailer.host",
        conversion_type="direct"
    ),
    "spring.mail.port": ConfigMapping(
        spring_property="spring.mail.port",
        quarkus_property="quarkus.mailer.port", 
        conversion_type="direct"
    ),
    "spring.mail.username": ConfigMapping(
        spring_property="spring.mail.username",
        quarkus_property="quarkus.mailer.username",
        conversion_type="direct"
    ),
    "spring.mail.password": ConfigMapping(
        spring_property="spring.mail.password",
        quarkus_property="quarkus.mailer.password",
        conversion_type="direct"
    ),
    
    # Application properties
    "spring.application.name": ConfigMapping(
        spring_property="spring.application.name",
        quarkus_property="quarkus.application.name",
        conversion_type="direct"
    ),
    "spring.profiles.active": ConfigMapping(
        spring_property="spring.profiles.active",
        quarkus_property="quarkus.profile",
        conversion_type="direct"
    ),
}

def convert_spring_config_to_quarkus(scanner_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Spring Boot configuration files to Quarkus format.
    
    Args:
        scanner_output: Output from scanner_analyzer_agent containing repository analysis
        
    Returns:
        ConfigPatch JSON with file diffs and migration notes
    """
    try:
        config_patch_result = {
            "success": True,
            "conversion_timestamp": __import__("datetime").datetime.now().isoformat(),
            "source_analysis": {
                "repo_path": scanner_output.get("repo_path", ""),
                "total_modules": scanner_output.get("total_modules", 0)
            },
            "config_patches": [],
            "environment_variables": [],
            "secrets_identified": [],
            "migration_summary": {
                "total_config_files": 0,
                "properties_migrated": 0,
                "manual_migrations_required": 0,
                "deprecated_properties": 0,
                "secrets_found": 0
            },
            "migration_notes": []
        }
        
        repo_path = Path(scanner_output.get("repo_path", ""))
        if not repo_path.exists():
            return {
                "success": False,
                "error": f"Repository path does not exist: {repo_path}"
            }
        
        # Find configuration files in the repository
        config_files = _find_config_files(repo_path)
        config_patch_result["migration_summary"]["total_config_files"] = len(config_files)
        
        all_env_vars = []
        all_secrets = []
        
        # Process each configuration file
        for config_file in config_files:
            try:
                patch = _process_config_file(config_file, repo_path)
                if patch:
                    config_patch_result["config_patches"].append({
                        "file_path": patch.file_path,
                        "original_content": patch.original_content,
                        "patched_content": patch.patched_content,
                        "diff_summary": patch.diff_summary,
                        "migration_notes": patch.migration_notes,
                        "environment_variables": patch.environment_variables,
                        "secrets_identified": patch.secrets_identified
                    })
                    
                    all_env_vars.extend(patch.environment_variables)
                    all_secrets.extend(patch.secrets_identified)
                    config_patch_result["migration_summary"]["properties_migrated"] += len(patch.diff_summary)
                    
            except Exception as e:
                logger.warning(f"Error processing config file {config_file}: {e}")
                config_patch_result["migration_notes"].append(f"Failed to process {config_file}: {str(e)}")
        
        # Deduplicate environment variables and secrets
        config_patch_result["environment_variables"] = list(set(all_env_vars))
        config_patch_result["secrets_identified"] = list(set(all_secrets))
        config_patch_result["migration_summary"]["secrets_found"] = len(all_secrets)
        
        # Add general migration recommendations
        config_patch_result["general_recommendations"] = _get_config_migration_recommendations(config_patch_result)
        
        return ensure_json_serializable(config_patch_result)
        
    except Exception as e:
        logger.error(f"Error in config conversion: {e}")
        return ensure_json_serializable({
            "success": False,
            "error": str(e),
            "message": "Failed to convert configuration files"
        })

def _find_config_files(repo_path: Path) -> List[Path]:
    """Find Spring Boot configuration files in the repository."""
    config_files = []
    
    # Common Spring Boot config file patterns
    config_patterns = [
        "**/application.properties",
        "**/application.yml", 
        "**/application.yaml",
        "**/application-*.properties",
        "**/application-*.yml",
        "**/application-*.yaml"
    ]
    
    for pattern in config_patterns:
        config_files.extend(repo_path.glob(pattern))
    
    # Remove duplicates and sort
    config_files = sorted(list(set(config_files)))
    
    return config_files

def _process_config_file(config_file: Path, repo_path: Path) -> Optional[ConfigPatch]:
    """Process a single configuration file."""
    if not config_file.exists():
        return None
        
    try:
        original_content = config_file.read_text(encoding='utf-8')
        
        if config_file.suffix in ['.yml', '.yaml']:
            patched_content, diff_summary, migration_notes, env_vars, secrets = _convert_yaml_config(original_content)
        else:
            patched_content, diff_summary, migration_notes, env_vars, secrets = _convert_properties_config(original_content)
        
        relative_path = str(config_file.relative_to(repo_path))
        
        return ConfigPatch(
            file_path=relative_path,
            original_content=original_content,
            patched_content=patched_content,
            diff_summary=diff_summary,
            migration_notes=migration_notes,
            environment_variables=env_vars,
            secrets_identified=secrets
        )
        
    except Exception as e:
        logger.error(f"Error processing config file {config_file}: {e}")
        return None

def _convert_properties_config(content: str) -> Tuple[str, List[str], List[str], List[str], List[str]]:
    """Convert Spring Boot .properties file to Quarkus format."""
    lines = content.split('\n')
    converted_lines = []
    diff_summary = []
    migration_notes = []
    env_vars = []
    secrets = []
    
    for line in lines:
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            converted_lines.append(line)
            continue
            
        # Parse property line
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Check for environment variables
            if '${' in value:
                env_var_match = re.findall(r'\$\{([^}]+)\}', value)
                env_vars.extend(env_var_match)
            
            # Check for potential secrets
            if _is_potential_secret(key, value):
                secrets.append(key)
            
            # Convert property using mapping table
            if key in CONFIG_MAPPING_TABLE:
                mapping = CONFIG_MAPPING_TABLE[key]
                
                if mapping.conversion_type == "direct":
                    new_line = f"{mapping.quarkus_property}={value}"
                    converted_lines.append(new_line)
                    diff_summary.append(f"Converted: {key} → {mapping.quarkus_property}")
                    
                elif mapping.conversion_type == "transform":
                    converted_value = _apply_transformation(key, value, mapping.transformation_rule)
                    new_line = f"{mapping.quarkus_property}={converted_value}"
                    converted_lines.append(new_line)
                    diff_summary.append(f"Transformed: {key} → {mapping.quarkus_property}")
                    if mapping.migration_notes:
                        migration_notes.append(f"{key}: {mapping.migration_notes}")
                        
                elif mapping.conversion_type == "manual":
                    converted_lines.append(f"# MANUAL MIGRATION REQUIRED: {line}")
                    converted_lines.append(f"# {mapping.migration_notes}")
                    diff_summary.append(f"Manual migration required: {key}")
                    migration_notes.append(f"{key}: {mapping.migration_notes}")
                    
            else:
                # Property not in mapping table - keep as is but add comment
                converted_lines.append(f"# REVIEW REQUIRED: {line}")
                converted_lines.append(line)
                diff_summary.append(f"Review required: {key} (no mapping found)")
                migration_notes.append(f"Property {key} requires manual review")
        else:
            converted_lines.append(line)
    
    return '\n'.join(converted_lines), diff_summary, migration_notes, env_vars, secrets

def _convert_yaml_config(content: str) -> Tuple[str, List[str], List[str], List[str], List[str]]:
    """Convert Spring Boot YAML file to Quarkus format."""
    try:
        yaml_data = yaml.safe_load(content)
        if not yaml_data:
            return content, [], [], [], []
            
        converted_data = {}
        diff_summary = []
        migration_notes = []
        env_vars = []
        secrets = []
        
        # Flatten YAML to dot notation for processing
        flat_properties = _flatten_yaml(yaml_data)
        
        for key, value in flat_properties.items():
            # Check for environment variables
            if isinstance(value, str) and '${' in value:
                env_var_match = re.findall(r'\$\{([^}]+)\}', value)
                env_vars.extend(env_var_match)
            
            # Check for potential secrets
            if _is_potential_secret(key, str(value)):
                secrets.append(key)
            
            # Convert property using mapping table
            if key in CONFIG_MAPPING_TABLE:
                mapping = CONFIG_MAPPING_TABLE[key]
                
                if mapping.conversion_type == "direct":
                    _set_nested_dict(converted_data, mapping.quarkus_property, value)
                    diff_summary.append(f"Converted: {key} → {mapping.quarkus_property}")
                    
                elif mapping.conversion_type == "transform":
                    converted_value = _apply_transformation(key, value, mapping.transformation_rule)
                    _set_nested_dict(converted_data, mapping.quarkus_property, converted_value)
                    diff_summary.append(f"Transformed: {key} → {mapping.quarkus_property}")
                    if mapping.migration_notes:
                        migration_notes.append(f"{key}: {mapping.migration_notes}")
                        
                elif mapping.conversion_type == "manual":
                    # Add as comment in YAML
                    comment_key = f"_manual_migration_{key.replace('.', '_')}"
                    _set_nested_dict(converted_data, comment_key, f"MANUAL: {key} = {value} | {mapping.migration_notes}")
                    diff_summary.append(f"Manual migration required: {key}")
                    migration_notes.append(f"{key}: {mapping.migration_notes}")
                    
            else:
                # Property not in mapping table - add review comment
                comment_key = f"_review_required_{key.replace('.', '_')}"
                _set_nested_dict(converted_data, comment_key, f"REVIEW: {key} = {value}")
                diff_summary.append(f"Review required: {key} (no mapping found)")
                migration_notes.append(f"Property {key} requires manual review")
        
        # Convert back to YAML
        converted_content = yaml.dump(converted_data, default_flow_style=False, allow_unicode=True)
        
        return converted_content, diff_summary, migration_notes, env_vars, secrets
        
    except Exception as e:
        logger.error(f"Error converting YAML: {e}")
        return content, [], [f"YAML conversion failed: {str(e)}"], [], []

def _flatten_yaml(data: Dict, prefix: str = '') -> Dict[str, Any]:
    """Flatten nested YAML to dot notation."""
    flattened = {}
    
    for key, value in data.items():
        new_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            flattened.update(_flatten_yaml(value, new_key))
        else:
            flattened[new_key] = value
    
    return flattened

def _set_nested_dict(data: Dict, key_path: str, value: Any) -> None:
    """Set value in nested dictionary using dot notation."""
    keys = key_path.split('.')
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value

def _apply_transformation(key: str, value: Any, transformation_rule: str) -> Any:
    """Apply transformation rule to convert property value."""
    if not transformation_rule:
        return value
        
    # Handle specific transformation rules
    if "redis://" in transformation_rule and key in ["spring.redis.host", "spring.redis.port"]:
        # Will be handled when both host and port are processed together
        return value
        
    if "drop-and-create" in transformation_rule:
        # JPA DDL transformation
        ddl_mapping = {
            "create": "create",
            "update": "update", 
            "create-drop": "drop-and-create",
            "validate": "validate",
            "none": "none"
        }
        return ddl_mapping.get(str(value), value)
    
    return value

def _is_potential_secret(key: str, value: str) -> bool:
    """Check if a property might contain sensitive information."""
    secret_keywords = [
        'password', 'secret', 'key', 'token', 'api-key', 'private',
        'credential', 'auth', 'certificate', 'keystore', 'truststore'
    ]
    
    key_lower = key.lower()
    return any(keyword in key_lower for keyword in secret_keywords) and len(str(value)) > 0

def _get_config_migration_recommendations(config_result: Dict[str, Any]) -> List[str]:
    """Generate configuration migration recommendations."""
    recommendations = []
    
    total_files = config_result["migration_summary"]["total_config_files"]
    secrets_count = config_result["migration_summary"]["secrets_found"]
    env_vars_count = len(config_result["environment_variables"])
    
    if total_files > 0:
        recommendations.append(f"Processed {total_files} configuration files")
        
    if secrets_count > 0:
        recommendations.append(f"Found {secrets_count} potential secrets - consider using Quarkus Vault or environment variables")
        recommendations.append("Review all password/key properties for proper secret management")
        
    if env_vars_count > 0:
        recommendations.append(f"Found {env_vars_count} environment variable references - verify compatibility")
        
    # Add general Quarkus config recommendations
    recommendations.extend([
        "Test all configuration changes in Quarkus dev mode",
        "Consider using Quarkus config profiles for different environments", 
        "Review logging configuration - Quarkus uses different log categories",
        "Database configuration may need fine-tuning for connection pooling",
        "Security configuration requires significant manual migration",
        "Validate all externalized configuration works in containerized environments"
    ])
    
    return recommendations
