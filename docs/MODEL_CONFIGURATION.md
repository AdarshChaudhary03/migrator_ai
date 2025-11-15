# Model Configuration

## Environment Variables

All agents in this migration system now use environment variables for model configuration instead of hardcoded values.

### Required Environment Variables

```bash
# Primary model configuration
LLM_MODEL=gemini-2.0-flash
```

### Optional Environment Variables

```bash
# Model behavior parameters
LLM_TEMPERATURE=0.1        # Controls randomness (0.0 to 2.0)
LLM_MAX_TOKENS=8192        # Maximum tokens per response
LLM_TOP_P=0.9             # Nucleus sampling parameter
LLM_TOP_K=40              # Top-K sampling parameter
```

## Supported Models

The system supports various LLM models depending on your ADK configuration:

- `gemini-2.0-flash` (default)
- `gemini-2.0-flash-exp`
- `gemini-1.5-pro`
- `gpt-4o`
- `claude-3-5-sonnet-20241022`

## Setup Instructions

1. **Copy the example environment file:**

   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file with your preferred model:**

   ```bash
   # Edit .env file
   LLM_MODEL=your-preferred-model
   ```

3. **Load environment variables (if needed):**

   ```bash
   # For bash/zsh
   source .env

   # Or export manually
   export LLM_MODEL=gemini-2.0-flash
   ```

## How It Works

The `utils/model_config.py` utility provides:

- `get_llm_model()` - Returns the model name from `LLM_MODEL` environment variable
- `get_model_config()` - Returns complete model configuration including temperature, tokens, etc.

All agents now import and use this utility:

```python
from utils.model_config import get_llm_model

agent = LlmAgent(
    name="agent_name",
    model=get_llm_model(),  # Uses environment variable
    # ... other parameters
)
```

## Benefits

- **Flexibility**: Change models without code modifications
- **Environment-specific**: Use different models for dev/staging/production
- **Centralized**: All model configuration in one place
- **Fallback**: Defaults to gemini-2.0-flash if environment variable not set
