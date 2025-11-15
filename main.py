"""
Main entry point for migrator-ai-v3
Exposes the root_migrator agent for adk web interface
"""

import os
import sys

# Add the project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the main agent
from agents.root_migrator.agent import root_agent

# Export for adk web to discover
agent = root_agent

def main():
    print("Hello from migrator-ai-v3!")
    print(f"Root migrator agent loaded: {agent.name}")


if __name__ == "__main__":
    main()
