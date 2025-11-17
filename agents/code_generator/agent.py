import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_loader import load_instructions_file
from utils.model_config import get_llm_model
from .code_generation_tools import (
    create_project_structure,
    write_source_file,
    write_build_file,
    write_test_file,
    write_configuration_file,
    write_documentation_file,
    write_docker_files,
    validate_project_structure
)

code_generator_agent = LlmAgent(
    name="code_generator_agent",
    model="gemini-2.5-flash",
    instruction=load_instructions_file("agents/code_generator/instructions.txt"),
    description=load_instructions_file("agents/code_generator/description.txt"),
    tools=[
        create_project_structure,
        write_source_file,
        write_build_file,
        write_test_file,
        write_configuration_file,
        write_documentation_file,
        write_docker_files,
        validate_project_structure
    ]
)# Export as root_agent for ADK to find
root_agent = code_generator_agent
