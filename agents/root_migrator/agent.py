import os
import sys
from google.adk.agents import ParallelAgent,SequentialAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_loader import load_instructions_file
from agents.repo_ingestor.agent import repo_ingestor_agent
from agents.scanner_analyzer.agent import scanner_analyzer_agent
from agents.dependency_mapper.agent import dependency_mapper_agent
from agents.config_mapper.agent import config_mapper_agent
from agents.ast_transformer.agent import ast_transformer_agent
from agents.build_script_converter.agent import build_script_converter_agent
from agents.test_adapter.agent import test_adapter_agent
from agents.code_generator.agent import code_generator_agent

ast_transformer_agent = ParallelAgent(
    name="ast_transformer_agent",
    sub_agents=[ast_transformer_agent, build_script_converter_agent, test_adapter_agent],
)

root_agent = SequentialAgent(
    name="root_migrator_agent",
    sub_agents=[
        repo_ingestor_agent, 
        scanner_analyzer_agent, 
        dependency_mapper_agent, 
        config_mapper_agent, 
        ast_transformer_agent,
        code_generator_agent
    ],
    description=load_instructions_file("agents/root_migrator/description.txt"),
)