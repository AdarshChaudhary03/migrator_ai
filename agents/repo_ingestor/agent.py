import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_loader import load_instructions_file
from tools.git_tool import ingest_repository
from utils.agent_callbacks import wrap_tools_for_agent

# Load environment variables from .env
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass

MODEL_NAME = os.getenv('LLM_MODEL', 'gemini-2.5-flash')
print(f"Using LLM Model: {MODEL_NAME}")

repo_ingestor_agent = LlmAgent(
    name="repo_ingestor_agent",
    model=MODEL_NAME,
    tools=wrap_tools_for_agent("repo_ingestor_agent", [ingest_repository]),
    instruction=load_instructions_file("agents/repo_ingestor/instructions.txt"),
    description=load_instructions_file("agents/repo_ingestor/description.txt"),
    output_key="repo_ingestor_output",
)

# Export as root_agent for ADK to find
root_agent = repo_ingestor_agent
