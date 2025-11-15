import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from utils.file_loader import load_instructions_file
from utils.model_config import get_llm_model
from tools.ast_transformation_tools import transform_spring_to_quarkus_code

ast_transformer_agent = LlmAgent(
    name="ast_transformer_agent",
    model="gemini-2.0-flash",
    tools=[transform_spring_to_quarkus_code],
    instruction=load_instructions_file("agents/ast_transformer/instructions.txt"),
    description=load_instructions_file("agents/ast_transformer/description.txt"),
    output_key="ast_transformer_output",
)
