import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from utils.file_loader import load_instructions_file
from utils.model_config import get_llm_model
from tools.build_script_conversion_tools import convert_build_scripts_to_quarkus

build_script_converter_agent = LlmAgent(
    name="build_script_converter_agent",
    model="gemini-2.0-flash",
    tools=[convert_build_scripts_to_quarkus],
    instruction=load_instructions_file("agents/build_script_converter/instructions.txt"),
    description=load_instructions_file("agents/build_script_converter/description.txt"),
    output_key="build_script_converter_output",
)
