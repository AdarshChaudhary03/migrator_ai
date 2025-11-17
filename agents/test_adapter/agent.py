import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from utils.file_loader import load_instructions_file
from utils.model_config import get_llm_model
from tools.test_adaptation_tools import adapt_and_run_quarkus_tests

test_adapter_agent = LlmAgent(
    name="test_adapter_agent",
    model="gemini-2.5-flash",
    tools=[adapt_and_run_quarkus_tests],
    instruction=load_instructions_file("agents/test_adapter/instructions.txt"),
    description=load_instructions_file("agents/test_adapter/description.txt"),
    output_key="test_adapter_output",
)
# Export as root_agent for ADK to find
root_agent = test_adapter_agent
