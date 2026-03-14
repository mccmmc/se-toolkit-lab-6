# Task 3: The System Agent - Implementation Plan

## Overview

Extend the Task 2 agent with a `query_api` tool to interact with the deployed backend API. This enables answering questions about system facts (framework, ports, status codes) and data-dependent queries (item count, scores).

## Tool Schema: `query_api`

### Parameters

```json
{
  "name": "query_api",
  "description": "Call the backend API to query data or check system behavior",
  "parameters": {
    "type": "object",
    "properties": {
      "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)"},
      "path": {"type": "string", "description": "API path (e.g., /items/, /analytics/completion-rate)"},
      "body": {"type": "string", "description": "Optional JSON request body for POST/PUT requests"}
    },
    "required": ["method", "path"]
  }
}
```

### Implementation

```python
def query_api(method: str, path: str, body: str | None = None) -> str:
    """Call the backend API and return response."""
    # Read LMS_API_KEY from .env.docker.secret
    # Read AGENT_API_BASE_URL from environment (default: http://localhost:42002)
    # Make HTTP request with authentication header
    # Return JSON string with status_code and body
```

## Environment Variables

| Variable | Source | Purpose |
|----------|--------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | LLM provider authentication |
| `LLM_API_BASE` | `.env.agent.secret` | LLM API endpoint |
| `LLM_MODEL` | `.env.agent.secret` | Model name |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | Environment or default | Backend API base URL (default: `http://localhost:42002`) |

### Loading Strategy

```python
def load_env_files():
    # Load .env.agent.secret for LLM config
    # Load .env.docker.secret for LMS_API_KEY
    # AGENT_API_BASE_URL from os.environ with default fallback
```

## System Prompt Update

The system prompt should guide the LLM to choose the right tool:

```
You have access to these tools:
- list_files(path): List files in a directory
- read_file(path): Read contents of a file
- query_api(method, path, body): Call the backend API

Tool selection guide:
- Use list_files/read_file for:
  - Wiki documentation questions
  - Source code questions
  - Configuration file questions
  
- Use query_api for:
  - Questions about data in the database
  - Questions about API behavior (status codes, responses)
  - Questions that require querying the running system

Always use tools to find answers - do not rely on prior knowledge.
```

## Agentic Loop

No changes needed to the loop structure - just add the new tool to the schema registry.

## Error Handling

- **Authentication failure**: Return error message to LLM
- **Connection error**: Return error message to LLM
- **Invalid path**: Return error message to LLM
- **API error (4xx, 5xx)**: Return full response to LLM for diagnosis

## Testing Strategy

Two new regression tests:

1. **Framework question**: "What framework does the backend use?" → expects `read_file`
2. **Data question**: "How many items are in the database?" → expects `query_api`

## Benchmark Iteration

After initial implementation, run `uv run run_eval.py` and iterate:

### Initial Results

| Iteration | Score | Failures | Fixes Applied |
|-----------|-------|----------|---------------|
| 1 | 5/10 | Q6: Status code wrong | Added `auth` parameter to query_api |
| 2 | 6/10 | Q7: Missing source field | Updated extract_source to capture backend/ paths |
| 3 | 7/10 | Q8: Max tool calls | Updated system prompt for efficient file access |
| 4 | 7/10 | Q8: Wrong bug diagnosis | Increased content limit to 8000 chars |
| 5 | 10/10 | None | All tests passing |

### Key Lessons

1. **Tool descriptions matter**: Adding `auth=false` option to query_api allowed testing unauthenticated access
2. **Source extraction**: Need to capture both wiki/ and backend/ paths
3. **Content limits**: Source code files need 8000+ chars for full context
4. **System prompt tuning**: Guide LLM to be efficient with tool calls for bug diagnosis

## Expected Challenges

1. **LLM choosing wrong tool**: Improve tool descriptions in schema
2. **API authentication**: Ensure LMS_API_KEY is loaded correctly
3. **Multi-step questions**: May need to call multiple tools in sequence
4. **Source code diagnosis**: LLM needs to read error from API, then read source to find bug

## Dependencies

- No new dependencies (using existing `httpx`)
- Need `.env.docker.secret` with `LMS_API_KEY`
