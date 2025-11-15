"""
Tools package for migrator_ai_v3
Contains utility tools for repository operations and agent functionality.
"""

from .git_tool import ingest_repository
from .scanner_tools import scan_spring_boot_features, FeaturePattern, ModuleAnalysis
from .dependency_mapping_tools import map_spring_dependencies_to_quarkus, DependencyMapping, DependencyAction
from .config_mapping_tools import convert_spring_config_to_quarkus, ConfigMapping, ConfigPatch
from .ast_transformation_tools import transform_spring_to_quarkus_code, CodeTransformation, TransformationModule
from .build_script_conversion_tools import convert_build_scripts_to_quarkus, QuarkusExtension, BuildProfile, BuildPatch
from .test_adaptation_tools import adapt_and_run_quarkus_tests, TestConversion, TestExecutionResult, TestFailureAnalysis, AutomatedFixSuggestion

__all__ = [
    'ingest_repository',
    'scan_spring_boot_features',
    'FeaturePattern',
    'ModuleAnalysis',
    'map_spring_dependencies_to_quarkus',
    'DependencyMapping',
    'DependencyAction',
    'convert_spring_config_to_quarkus',
    'ConfigMapping',
    'ConfigPatch',
    'transform_spring_to_quarkus_code',
    'CodeTransformation',
    'TransformationModule',
    'convert_build_scripts_to_quarkus',
    'QuarkusExtension',
    'BuildProfile',
    'BuildPatch',
    'adapt_and_run_quarkus_tests',
    'TestConversion',
    'TestExecutionResult',
    'TestFailureAnalysis',
    'AutomatedFixSuggestion'
]
