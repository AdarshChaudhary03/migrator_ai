import os
import json
from pathlib import Path
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Iterable, List, Optional

# Try to use the existing serializer if available
try:
    from utils.subprocess_utils import ensure_json_serializable  # type: ignore
except Exception:
    def ensure_json_serializable(obj: Any) -> Any:  # fallback
        try:
            json.dumps(obj)
            return obj
        except Exception:
            return str(obj)

# Active report files per agent (single file aggregating all tool calls in a run)
_ACTIVE_REPORT_FILES: Dict[str, Path] = {}


def _load_env_dotenv(project_root: Optional[str] = None) -> None:
    """Best-effort .env loader without adding hard deps."""
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
        return
    except Exception:
        pass
    root = project_root or os.getcwd()
    env_path = os.path.join(root, '.env')
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


# Remove session id usage; we keep helper for backward compatibility but unused
def _session_id() -> str:
    return datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')


def _repo_name_from_kwargs(kwargs: Dict[str, Any]) -> Optional[str]:
    for key in ('repo_name',):
        if kwargs.get(key):
            return str(kwargs[key])
    # derive from repo_url
    ru = kwargs.get('repo_url') or kwargs.get('git_url')
    if isinstance(ru, str) and ru:
        name = ru.rstrip('/').split('/')[-1].replace('.git', '')
        return name or None
    # derive from repo_path/local_path
    for key in ('repo_path', 'local_path'):
        p = kwargs.get(key)
        if isinstance(p, str) and p:
            try:
                return Path(p).name
            except Exception:
                continue
    return None


def _reports_root(base_output_dir: str = './output') -> Path:
    p = Path(base_output_dir) / 'reports'
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_md(path: Path, text: str, mode: str = 'a') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding='utf-8') as f:
        f.write(text)
        if not text.endswith('\n'):
            f.write('\n')


def _md_header(title: str, level: int = 1) -> str:
    return f"{'#' * level} {title}\n\n"


def _md_kv_table(d: Dict[str, Any]) -> str:
    if not d:
        return "(no inputs)\n\n"
    rows = ["| Key | Value |", "| --- | --- |"]
    for k, v in d.items():
        try:
            val = json.dumps(ensure_json_serializable(v))
        except Exception:
            val = str(v)
        rows.append(f"| {k} | {val} |")
    return "\n".join(rows) + "\n\n"


def before_agent(agent_name: str, tool_name: str, kwargs: Dict[str, Any], base_output_dir: str = './output') -> Path:
    """Create (if needed) a single timestamped file for the agent and append BEFORE section."""
    _load_env_dotenv()
    # Initialize file once per agent run
    if agent_name not in _ACTIVE_REPORT_FILES:
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        agent_dir = _reports_root(base_output_dir) / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)
        file_path = agent_dir / f"{timestamp}.md"
        _ACTIVE_REPORT_FILES[agent_name] = file_path
        repo_name = _repo_name_from_kwargs(kwargs) or 'unknown-repo'
        _write_md(file_path, _md_header(f"Agent Report: {agent_name}"), mode='w')
        _write_md(file_path, f"Generated: {datetime.utcnow().isoformat()} UTC\nRepository: {repo_name}\n\n")
    else:
        file_path = _ACTIVE_REPORT_FILES[agent_name]
    _write_md(file_path, _md_header(f"Before: {tool_name}", level=2))
    _write_md(file_path, _md_kv_table(kwargs))
    return file_path


def after_agent(agent_name: str, tool_name: str, kwargs: Dict[str, Any], result: Any, base_output_dir: str = './output', file_path: Optional[Path] = None) -> Path:
    """Append AFTER section to the existing agent report file."""
    if file_path is None:
        # Fallback: ensure file exists
        file_path = _ACTIVE_REPORT_FILES.get(agent_name)
        if file_path is None:
            # Create a new file if before_agent was not called (edge case)
            timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
            agent_dir = _reports_root(base_output_dir) / agent_name
            agent_dir.mkdir(parents=True, exist_ok=True)
            file_path = agent_dir / f"{timestamp}.md"
            _ACTIVE_REPORT_FILES[agent_name] = file_path
            _write_md(file_path, _md_header(f"Agent Report: {agent_name}"), mode='w')
            _write_md(file_path, f"Generated: {datetime.utcnow().isoformat()} UTC\n\n")
    _write_md(file_path, _md_header(f"After: {tool_name}", level=2))
    try:
        payload = json.dumps(ensure_json_serializable(result), indent=2)
    except Exception:
        payload = str(result)
    _write_md(file_path, f"```json\n{payload}\n```\n\n")
    return file_path


def wrap_tools_for_agent(agent_name: str, tools: Iterable[Callable]) -> List[Callable]:
    """Wrap each tool so its before/after are logged into the agent's single report file."""
    wrapped: List[Callable] = []
    for func in tools:
        @wraps(func)
        def _wrapper(*args, __func: Callable = func, **kwargs):
            tool_name = getattr(__func, '__name__', 'tool')
            file_path = None
            try:
                file_path = before_agent(agent_name, tool_name, dict(kwargs))
            except Exception:
                pass
            result = __func(*args, **kwargs)
            try:
                after_agent(agent_name, tool_name, dict(kwargs), result, file_path=file_path)
            except Exception:
                pass
            return result
        wrapped.append(_wrapper)
    return wrapped


# Optional helper to reset active report files between pipeline runs
def reset_agent_reports():
    _ACTIVE_REPORT_FILES.clear()
