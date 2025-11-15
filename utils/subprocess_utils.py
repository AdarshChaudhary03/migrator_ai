"""
Common utilities for handling subprocess output and other shared functionality.
"""

def safe_decode_output(output) -> str:
    """
    Safely decode subprocess output to string to avoid JSON serialization errors.
    
    Args:
        output: Subprocess output (bytes, str, or None)
        
    Returns:
        String representation of the output
    """
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    if isinstance(output, bytes):
        return output.decode('utf-8', errors='replace')
    return str(output)

def ensure_json_serializable(data):
    """
    Ensure data is JSON serializable by converting bytes to strings.
    
    Args:
        data: Any data structure that might contain bytes
        
    Returns:
        JSON-serializable version of the data
    """
    if isinstance(data, bytes):
        return data.decode('utf-8', errors='replace')
    elif isinstance(data, dict):
        return {key: ensure_json_serializable(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [ensure_json_serializable(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(ensure_json_serializable(item) for item in data)
    else:
        return data
