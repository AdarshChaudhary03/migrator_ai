# Run root_migrator via ADK API (curl)

Prerequisites

- ADK server running from the `agents` directory:
  - cd <project_root>/agents
  - adk api_server --port 8888
- Credentials set for the LLM (required to avoid HTTP 500 on /run):
  - export GOOGLE_API_KEY="<your_api_key>"
  - Or configure Vertex AI: export VERTEX_PROJECT, VERTEX_LOCATION, GOOGLE_APPLICATION_CREDENTIALS

Notes

- If starting with a path (adk api_server ./agents) causes OpenAPI errors, start without the path from inside the `agents` dir, or uninstall MCP: `pip uninstall -y mcp model-context-protocol`.

Verify server

- curl -s http://localhost:8888/list-apps | jq -r '.'
  - Ensure `root_migrator` is listed.

Create a session

- USER_ID="cli-user"
- APP="root_migrator"
- SESSION_ID=$(curl -s -X POST "http://localhost:8888/apps/$APP/users/$USER_ID/sessions" -H 'Content-Type: application/json' -d '{}' | jq -r '.id')
- echo $SESSION_ID

Run root_migrator for a repo (non-streaming)

- REPO_URL="https://github.com/LahcenEzzara/spring-boot-explorer"
- curl -i -X POST http://localhost:8888/run \
  -H 'Content-Type: application/json' \
  -d '{
  "app_name": "root_migrator",
  "user_id": "'"$USER_ID"'",
    "session_id": "'"$SESSION_ID"'",
  "new_message": {
  "role": "user",
  "parts": [{"text": "'"$REPO_URL"'"}]
  },
  "streaming": false
  }'

Run with server-sent events (streaming)

- curl -N -X POST http://localhost:8888/run_sse \
  -H 'Content-Type: application/json' \
  -d '{
  "app_name": "root_migrator",
  "user_id": "'"$USER_ID"'",
    "session_id": "'"$SESSION_ID"'",
  "new_message": {
  "role": "user",
  "parts": [{"text": "'"$REPO_URL"'"}]
  },
  "streaming": true
  }'

Inspect session (optional)

- curl -s "http://localhost:8888/apps/$APP/users/$USER_ID/sessions/$SESSION_ID" | jq

Common issues

- HTTP 500 on /run: set GOOGLE_API_KEY or Vertex env; ensure model access.
- OpenAPI 500 when starting with a path: run server from `agents` dir; remove MCP if needed.
