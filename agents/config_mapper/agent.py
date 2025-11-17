import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from utils.file_loader import load_instructions_file
from utils.model_config import get_llm_model
from tools.config_mapping_tools import convert_spring_config_to_quarkus

config_mapper_agent = LlmAgent(
    name="config_mapper_agent",
    model="gemini-2.5-flash",
    tools=[convert_spring_config_to_quarkus],
    instruction=load_instructions_file("agents/config_mapper/instructions.txt"),
    description=load_instructions_file("agents/config_mapper/description.txt"),
    output_key="config_mapper_output",
)
# Export as root_agent for ADK to find
root_agent = config_mapper_agent
