import os
import uuid
import time
import asyncio
import streamlit as st
from datetime import datetime
import inspect
from pathlib import Path
import shutil

# Load .env manually (avoid extra dependency)
ENV_PATH = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            if k and v and k not in os.environ:
                os.environ[k] = v

# Import individual agents used in the root_migrator sequence
from agents.repo_ingestor.agent import repo_ingestor_agent
from agents.scanner_analyzer.agent import scanner_analyzer_agent
from agents.dependency_mapper.agent import dependency_mapper_agent
from agents.config_mapper.agent import config_mapper_agent
from agents.ast_transformer.agent import ast_transformer_agent
from agents.build_script_converter.agent import build_script_converter_agent
from agents.test_adapter.agent import test_adapter_agent
from agents.code_generator.agent import code_generator_agent

# Ordered pipeline matching root_migrator
PIPELINE = [
    repo_ingestor_agent,
    scanner_analyzer_agent,
    dependency_mapper_agent,
    config_mapper_agent,
    ast_transformer_agent,
    build_script_converter_agent,
    test_adapter_agent,
    code_generator_agent,
]

st.set_page_config(page_title="Migration UI", page_icon="🚀", layout="wide")
st.title("🚀 Spring Boot → Quarkus Migration (Direct Agent Mode)")
st.caption("Runs migration pipeline locally without ADK API server.")

repo_url = st.text_input("GitHub Repository URL", placeholder="https://github.com/username/spring-boot-repo")
user_id = st.text_input("User ID", value="ui-user")
start_btn = st.button("Start Migration", disabled=not repo_url)

# Container for logs
log_area = st.container()

DEFAULT_OUTPUT_DIR = "/tmp/migration-output"

# Enhanced tool invoker with state propagation
# (updated with alias mapping for parameter names)
def invoke_agent_tools(agent, repo_url: str, session_id: str, state: dict):
    events = []
    if not hasattr(agent, 'tools') or not agent.tools:
        return events, state

    # Maintain mirror keys for path values
    if 'local_path' in state and 'repo_path' not in state:
        state['repo_path'] = state['local_path']
    if 'repo_path' in state and 'local_path' not in state:
        state['local_path'] = state['repo_path']

    # Common alias mapping to translate expected parameter names to available state keys
    alias_map = {
        'repo_path': ['local_path', 'repo_root', 'repo_dir'],
        'project_path': ['local_path', 'repo_path'],
        'path': ['local_path', 'repo_path'],
        'repository_path': ['local_path', 'repo_path'],
        'repo_url': ['repo_url', 'git_url'],
        'git_url': ['repo_url'],
        'output_dir': ['output_dir'],
        'branch': ['branch'],
        # cross-agent payloads
        'scanner_output': ['scanner_output', 'scanner_analyzer_output', 'scan_result', 'scan_spring_boot_features_output'],
        'repo_ingestor_output': ['repo_ingestor_output', 'ingest_repository_output', 'repo_snapshot', 'ingestion_output'],
        'dependency_output': ['dependency_output', 'dependency_mapper_output', 'map_spring_dependencies_to_quarkus_output'],
        'config_output': ['config_output', 'config_mapper_output', 'convert_spring_config_to_quarkus_output'],
        # code generator helpers
        'target_path': ['target_path'],
        'base_path': ['base_path'],
        'repo_name': ['repo_name'],
    }

    # Nested lookup map for extracting values inside stored outputs
    nested_map = {
        'target_path': [
            ['ast_transformer_output', 'source_analysis', 'target_quarkus_path'],
            ['transform_spring_to_quarkus_code_output', 'source_analysis', 'target_quarkus_path'],
        ],
        'base_path': [
            ['create_project_structure_output', 'base_path'],
            ['ast_transformer_output', 'source_analysis', 'target_quarkus_path'],
        ],
    }

    def get_nested(state_dict, path_list):
        cur = state_dict
        try:
            for key in path_list:
                cur = cur[key]
            return cur
        except Exception:
            return None

    for tool in agent.tools:
        try:
            sig = inspect.signature(tool)
            param_names = list(sig.parameters.keys())
            kwargs = {}
            missing_required = []
            # Direct state match
            for name in param_names:
                if name in state:
                    kwargs[name] = state[name]
                    continue
                # Alias resolution
                if name in alias_map:
                    for candidate in alias_map[name]:
                        if candidate in state:
                            kwargs[name] = state[candidate]
                            break
                # Nested extraction
                if name not in kwargs and name in nested_map:
                    for p in nested_map[name]:
                        val = get_nested(state, p)
                        if val is not None:
                            kwargs[name] = val
                            break
                # Special derivations
                if name == 'repo_url' and name not in kwargs:
                    kwargs[name] = repo_url
                if name == 'output_dir' and name not in kwargs:
                    Path(DEFAULT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
                    kwargs[name] = DEFAULT_OUTPUT_DIR
                if name == 'branch' and name not in kwargs:
                    kwargs[name] = state.get('branch', 'main')
                if name == 'session_id' and name not in kwargs:
                    kwargs[name] = session_id
                if name == 'user_id' and name not in kwargs:
                    kwargs[name] = state.get('user_id', 'ui-user')
                if name == 'repo_name' and name not in kwargs:
                    ru = state.get('repo_url', repo_url)
                    if ru:
                        kwargs['repo_name'] = ru.rstrip('/').split('/')[-1].replace('.git', '')
                # Defaults
                if name not in kwargs and sig.parameters[name].default is not inspect._empty:
                    kwargs[name] = sig.parameters[name].default
                if name not in kwargs and sig.parameters[name].default is inspect._empty:
                    missing_required.append(name)

            # Ensure repo_path is set when required
            if 'repo_path' in param_names and 'repo_path' not in kwargs:
                if 'local_path' in state:
                    kwargs['repo_path'] = state['local_path']
                elif 'repo_path' in state:
                    kwargs['repo_path'] = state['repo_path']
                else:
                    ru = state.get('repo_url', repo_url)
                    repo_name = ru.rstrip('/').split('/')[-1].replace('.git', '') if ru else ''
                    candidate = str(Path(DEFAULT_OUTPUT_DIR) / repo_name) if repo_name else None
                    if candidate and Path(candidate).exists():
                        kwargs['repo_path'] = candidate
                    else:
                        missing_required.append('repo_path')

            # Only pass kwargs the tool actually accepts
            kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}

            # Special handling for code generator tools that may execute multiple times using patches
            tool_name = getattr(tool, '__name__', '')
            if tool_name in ('write_build_file', 'write_source_file', 'write_configuration_file', 'write_test_file'):
                # Resolve base paths
                target_temp = get_nested(state, ['ast_transformer_output', 'source_analysis', 'target_quarkus_path']) \
                               or get_nested(state, ['transform_spring_to_quarkus_code_output', 'source_analysis', 'target_quarkus_path'])
                base_persistent = get_nested(state, ['create_project_structure_output', 'base_path']) or state.get('base_path')

                # One-time copy of transformed sources/resources from AST temp to persistent base
                if target_temp and base_persistent and not state.get('_codegen_sources_copied'):
                    try:
                        for sub in ['src/main/java', 'src/test/java', 'src/main/resources']:
                            src_dir = Path(target_temp) / sub
                            dst_dir = Path(base_persistent) / sub
                            if src_dir.exists():
                                dst_dir.mkdir(parents=True, exist_ok=True)
                                # Copy tree
                                for root, dirs, files in os.walk(src_dir):
                                    rel = os.path.relpath(root, start=src_dir)
                                    target_dir = dst_dir / rel if rel != '.' else dst_dir
                                    target_dir.mkdir(parents=True, exist_ok=True)
                                    for f in files:
                                        shutil.copy2(os.path.join(root, f), str(target_dir))
                        state['_codegen_sources_copied'] = True
                        events.append({
                            'author': agent.name,
                            'content': {'parts': [{'text': f"Copied transformed sources/resources from {target_temp} to {base_persistent}."}]},
                            'timestamp': time.time(),
                            'turn_complete': True,
                        })
                    except Exception as copy_err:
                        events.append({
                            'author': agent.name,
                            'content': {'parts': [{'text': f"Warning: failed to copy sources: {copy_err}"}]},
                            'timestamp': time.time(),
                            'turn_complete': True,
                        })

                executed = 0
                if tool_name == 'write_build_file':
                    patches = get_nested(state, ['build_script_converter_output', 'build_patches']) or \
                              get_nested(state, ['convert_build_scripts_to_quarkus_output', 'build_patches']) or []
                    for p in patches:
                        content = p.get('transformed_content') or p.get('new_content') or p.get('content')
                        if not content:
                            continue
                        file_path = p.get('file_path', '')
                        file_type = 'pom.xml' if file_path.endswith('pom.xml') else ('build.gradle' if 'build.gradle' in file_path else kwargs.get('file_type', 'pom.xml'))
                        call_kwargs = {k: v for k, v in kwargs.items()}
                        call_kwargs.update({'file_content': content, 'file_type': file_type})
                        if 'base_path' in sig.parameters and base_persistent:
                            call_kwargs['base_path'] = base_persistent
                        tool(**call_kwargs)
                        executed += 1
                else:
                    # Source/config/test files from AST/code/config patches
                    if tool_name == 'write_source_file':
                        patches = get_nested(state, ['ast_transformer_output', 'code_patches']) or \
                                  get_nested(state, ['transform_spring_to_quarkus_code_output', 'code_patches']) or []
                        # support both with/without leading slash
                        markers = ['src/main/java/', '/src/main/java/']
                    elif tool_name == 'write_configuration_file':
                        patches = get_nested(state, ['config_mapper_output', 'config_patches']) or \
                                  get_nested(state, ['convert_spring_config_to_quarkus_output', 'config_patches']) or []
                        markers = ['src/main/resources/', '/src/main/resources/']
                    else:  # write_test_file
                        patches = get_nested(state, ['ast_transformer_output', 'code_patches']) or \
                                  get_nested(state, ['transform_spring_to_quarkus_code_output', 'code_patches']) or []
                        markers = ['src/test/java/', '/src/test/java/']
                    for p in patches:
                        content = p.get('transformed_content') or p.get('patched_content') or p.get('content')
                        if not content:
                            continue
                        fpath = p.get('file_path', '')
                        rel = None
                        if target_temp and fpath and str(fpath).startswith(str(target_temp)):
                            try:
                                rel = os.path.relpath(fpath, start=str(target_temp))
                            except Exception:
                                rel = None
                        if not rel and fpath:
                            for m in markers:
                                if m in fpath:
                                    rel = fpath.split(m, 1)[1]
                                    rel = m.lstrip('/') + rel
                                    break
                        if not rel and fpath and any(fpath.startswith(m) for m in ['src/', '/src/']):
                            rel = fpath.lstrip('/')
                        if not rel:
                            continue
                        call_kwargs = {k: v for k, v in kwargs.items()}
                        call_kwargs.update({'file_path': rel, 'content': content})
                        if 'base_path' in sig.parameters and base_persistent:
                            call_kwargs['base_path'] = base_persistent
                        tool(**call_kwargs)
                        executed += 1
                events.append({
                    'author': agent.name,
                    'content': {'parts': [{'text': f"Tool {tool_name} executed {executed} time(s). Base path: {base_persistent or ''}."}]},
                    'timestamp': time.time(),
                    'turn_complete': True,
                })
                continue

            # If required params are still missing, skip this tool
            if any(name for name, p in sig.parameters.items() if p.default is inspect._empty and name not in kwargs):
                events.append({
                    'author': agent.name,
                    'content': {'parts': [{'text': f"Skipping tool {tool.__name__} due to missing required params: {[n for n, p in sig.parameters.items() if p.default is inspect._empty and n not in kwargs]}\nAvailable state keys: {list(state.keys())[:40]}"}]},
                    'timestamp': time.time(),
                    'turn_complete': True,
                })
                continue

            result = tool(**kwargs)
            if isinstance(result, dict):
                state.update(result)
                # Store under agent output_key if available
                try:
                    output_key = getattr(agent, 'output_key', None)
                    if output_key:
                        state[output_key] = result
                except Exception:
                    pass
                # Store under tool-specific key
                state[f"{tool.__name__}_output"] = result
                # Canonical keys for known stages
                if tool.__name__ == 'ingest_repository' and 'repo_ingestor_output' not in state:
                    state['repo_ingestor_output'] = result
                if tool.__name__ == 'scan_spring_boot_features' and 'scanner_output' not in state:
                    state['scanner_output'] = result
                if tool.__name__ == 'map_spring_dependencies_to_quarkus' and 'dependency_output' not in state:
                    state['dependency_output'] = result
                if tool.__name__ == 'convert_spring_config_to_quarkus' and 'config_output' not in state:
                    state['config_output'] = result
                # Keep mirror keys updated after each tool (state only)
                if 'local_path' in state and 'repo_path' not in state:
                    state['repo_path'] = state['local_path']
                if 'repo_path' in state and 'local_path' not in state:
                    state['local_path'] = state['repo_path']
            events.append({
                'author': agent.name,
                'content': {'parts': [{'text': f"Tool {tool.__name__} executed.\nResolved kwargs (filtered): {kwargs}\nState keys now: {list(state.keys())[:40]}\nResult (truncated): {str(result)[:800]}"}]},
                'timestamp': time.time(),
                'turn_complete': True,
            })
        except Exception as e:
            events.append({
                'author': agent.name,
                'content': {'parts': [{'text': f"Error running tool {tool.__name__}: {e}\nSignature params: {param_names}\nState keys at error: {list(state.keys())}"}]},
                'error_message': str(e),
                'timestamp': time.time(),
                'turn_complete': True,
            })
    return events, state

# Replace run_pipeline to use direct tool invocation with state passing
def run_pipeline(repo_url: str, user_id: str):
    session_id = str(uuid.uuid4())
    all_events = []
    start_time = time.time()
    error = None
    state = {"repo_url": repo_url, "user_id": user_id}
    for agent in PIPELINE:
        try:
            tool_events, state = invoke_agent_tools(agent, repo_url, session_id, state)
            all_events.extend(tool_events)
        except Exception as e:
            error = f"Agent {agent.name} failed: {e}"
            break
    duration = time.time() - start_time
    # Final summary event
    all_events.append({
        "author": "pipeline",
        "content": {"parts": [{"text": f"Pipeline completed. Final state keys: {list(state.keys())}."}]},
        "timestamp": time.time(),
        "turn_complete": True,
    })
    return session_id, all_events, duration, error

if start_btn and repo_url:
    with st.spinner("Running migration pipeline..."):
        session_id, events, duration, error = run_pipeline(repo_url, user_id)

    st.subheader("Run Summary")
    st.write({
        "session_id": session_id,
        "repo_url": repo_url,
        "events_count": len(events),
        "duration_sec": round(duration, 2)
    })

    if error:
        st.error(error)
    elif not events:
        st.warning("No events returned by pipeline.")

    st.session_state["last_run"] = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "repo_url": repo_url,
        "events": events,
        "error": error
    }

# Display last run events
if "last_run" in st.session_state:
    st.subheader("Events")
    last = st.session_state["last_run"]
    for i, ev in enumerate(last["events"]):
        with st.expander(f"Event {i+1} - {ev.get('author', 'unknown')}", expanded=i == 0):
            meta = {k: v for k, v in ev.items() if k not in ("content",)}
            st.json(meta)
            content = ev.get("content") or {}
            parts = content.get("parts") or []
            for p in parts:
                if p.get("text"):
                    st.text_area("Text", value=p["text"], height=160, key=f"ev_text_{i}")
                else:
                    st.json(p)

# Minimal footer
st.markdown("---")
st.caption("Direct pipeline execution. Future: parallel transforms, artifacts, progress bars.")
