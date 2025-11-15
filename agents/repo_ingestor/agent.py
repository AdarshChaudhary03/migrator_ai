import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from utils.file_loader import load_instructions_file
from utils.model_config import get_llm_model
from tools.git_tool import ingest_repository

repo_ingestor_agent = LlmAgent(
    name="repo_ingestor_agent",
    model="gemini-2.0-flash",
    tools=[ingest_repository],
    instruction=load_instructions_file("agents/repo_ingestor/instructions.txt"),
    description=load_instructions_file("agents/repo_ingestor/description.txt"),
    output_key="repo_ingestor_output",
)