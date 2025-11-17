import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from utils.file_loader import load_instructions_file
from utils.model_config import get_llm_model
from tools.scanner_tools import scan_spring_boot_features

scanner_analyzer_agent = LlmAgent(
    name="scanner_analyzer_agent",
    model="gemini-2.5-flash",
    tools=[scan_spring_boot_features],
    instruction=load_instructions_file("agents/scanner_analyzer/instructions.txt"),
    description=load_instructions_file("agents/scanner_analyzer/description.txt"),
    output_key="scanner_analyzer_output",
)

# Export as root_agent for ADK to find
root_agent = scanner_analyzer_agent
