import os
import sys
from google.adk.agents import LlmAgent

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.file_loader import load_instructions_file
from tools.build_script_conversion_tools import convert_build_scripts_to_quarkus
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

build_script_converter_agent = LlmAgent(
    name="build_script_converter_agent",
    model=MODEL_NAME,
    tools=wrap_tools_for_agent("build_script_converter_agent", [convert_build_scripts_to_quarkus]),
    instruction=load_instructions_file("agents/build_script_converter/instructions.txt"),
    description=load_instructions_file("agents/build_script_converter/description.txt"),
    output_key="build_script_converter_output",
)
# Export as root_agent for ADK to find
root_agent = build_script_converter_agent
