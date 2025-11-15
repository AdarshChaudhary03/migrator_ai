import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from utils.file_loader import load_instructions_file
from utils.model_config import get_llm_model
from tools.dependency_mapping_tools import map_spring_dependencies_to_quarkus

dependency_mapper_agent = LlmAgent(
    name="dependency_mapper_agent",
    model="gemini-2.0-flash",
    tools=[map_spring_dependencies_to_quarkus],
    instruction=load_instructions_file("agents/dependency_mapper/instructions.txt"),
    description=load_instructions_file("agents/dependency_mapper/description.txt"),
    output_key="dependency_mapper_output",
)
