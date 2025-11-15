import os
from typing import Optional

def get_llm_model(default_model: str = "gemini-2.5-flash") -> str:
    """
    Get LLM model name from environment variable with fallback to default.
    
    Args:
        default_model: Default model to use if environment variable is not set
        
    Returns:
        Model name to use for LLM agents
    """
    return os.getenv("LLM_MODEL", default_model)

def get_model_config() -> dict:
    """
    Get complete model configuration from environment variables.
    
    Returns:
        Dictionary containing model configuration
    """
    config = {
        "model": get_llm_model(),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "8192")),
    }
    
    # Add additional model parameters if specified in environment
    if os.getenv("LLM_TOP_P"):
        config["top_p"] = float(os.getenv("LLM_TOP_P"))
    
    if os.getenv("LLM_TOP_K"):
        config["top_k"] = int(os.getenv("LLM_TOP_K"))
    
    return config
