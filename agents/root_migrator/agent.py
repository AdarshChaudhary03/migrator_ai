import os
import sys
from google.adk.agents import SequentialAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_loader import load_instructions_file
from agents.repo_ingestor.agent import repo_ingestor_agent

root_agent = SequentialAgent(
    name="root_migrator_agent",
    sub_agents=[repo_ingestor_agent],
    description=load_instructions_file("agents/root_migrator/description.txt"),
)