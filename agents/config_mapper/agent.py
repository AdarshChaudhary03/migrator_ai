import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_loader import load_instructions_file
from tools.config_mapping_tools import convert_spring_config_to_quarkus
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

config_mapper_agent = LlmAgent(
    name="config_mapper_agent",
    model=MODEL_NAME,
    tools=wrap_tools_for_agent("config_mapper_agent", [convert_spring_config_to_quarkus]),
    instruction=load_instructions_file("agents/config_mapper/instructions.txt"),
    description=load_instructions_file("agents/config_mapper/description.txt"),
    output_key="config_mapper_output",
)
# Export as root_agent for ADK to find
root_agent = config_mapper_agent
