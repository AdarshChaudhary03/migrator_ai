import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_loader import load_instructions_file
from tools.test_adaptation_tools import adapt_and_run_quarkus_tests
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

test_adapter_agent = LlmAgent(
    name="test_adapter_agent",
    model=MODEL_NAME,
    tools=wrap_tools_for_agent("test_adapter_agent", [adapt_and_run_quarkus_tests]),
    instruction=load_instructions_file("agents/test_adapter/instructions.txt"),
    description=load_instructions_file("agents/test_adapter/description.txt"),
    output_key="test_adapter_output",
)
# Export as root_agent for ADK to find
root_agent = test_adapter_agent
