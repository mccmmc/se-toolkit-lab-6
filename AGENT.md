# Agent Architecture

## Overview

This project implements a CLI agent (`agent.py`) that connects to an LLM and returns structured JSON answers. The agent has tools (`read_file`, `list_files`, `query_api`) to navigate the project wiki, read source code, and query the backend API. An agentic loop enables iterative tool use to find answers.

## LLM Provider

- **Provider**: Qwen Code API
- **Model**: `qwen3-coder-plus`
- **API Type**: OpenAI-compatible chat completions API

The Qwen Code API was chosen because it provides:
- 1000 free requests per day
- Availability in Russia
- No credit card required
- Strong tool-calling capabilities

## Architecture

### Input/Output Flow

```
User question (CLI argument)
    ↓
agent.py (parse arguments, load config)
    ↓
Agentic Loop:
  - Send question + tool schemas to LLM
  - If LLM returns tool_calls → execute tools, feed results back
  - If LLM returns answer → extract source, output JSON
    ↓
JSON output to stdout
```

### Components

1. **Environment Loading** (`load_env()`)
   - Reads `.env.agent.secret` for LLM config (`LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`)
   - Reads `.env.docker.secret` for backend API key (`LMS_API_KEY`)
   - Only sets environment variables if not already defined

2. **Configuration Validation** (`get_llm_config()`, `get_api_config()`)
   - Validates that all required environment variables are present
   - Exits with error code 1 if any are missing

3. **Tools**
   - `read_file(path)`: Read a file from the project repository
   - `list_files(path)`: List files in a directory
   - `query_api(method, path, body, auth)`: Call the backend API with optional authentication
   - All tools validate paths to prevent directory traversal attacks

4. **LLM API Call** (`call_ll()`)
   - Sends async HTTP POST to `{LLM_API_BASE}/chat/completions`
   - Uses `httpx` for async HTTP requests
   - Supports tool schemas for function calling
   - 60-second timeout

5. **Agentic Loop** (`run_agentic_loop()`)
   - Maintains conversation history with the LLM
   - Executes tool calls and feeds results back
   - Prevents duplicate file reads
   - Stops after 10 tool calls or when LLM provides final answer
   - Extracts source reference from the answer

6. **Main Entry Point** (`main()`)
   - Parses command-line argument (the question)
   - Handles PowerShell quoting issues by joining arguments
   - Orchestrates the flow
   - Outputs JSON to stdout
   - All debug output goes to stderr

### Output Format

The agent outputs a single JSON line to stdout:

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

- `answer` (string): The LLM's response to the question
- `source` (string): Reference to the file/section used (wiki or backend)
- `tool_calls` (array): List of tool calls made during execution

## Tools

### `read_file`

Read a file from the project repository.

- **Parameters:** `path` (string) — relative path from project root
- **Returns:** File contents as a string, or an error message
- **Security:** Validates path to prevent directory traversal

### `list_files`

List files and directories at a given path.

- **Parameters:** `path` (string) — relative directory path from project root
- **Returns:** Newline-separated listing of entries, or error message
- **Security:** Validates path to prevent directory traversal

### `query_api`

Call the backend API to query data or check system behavior.

- **Parameters:** 
  - `method` (string) — HTTP method (GET, POST, PUT, DELETE)
  - `path` (string) — API path (e.g., `/items/`, `/analytics/completion-rate`)
  - `body` (string, optional) — JSON request body for POST/PUT requests
  - `auth` (boolean, default: true) — Whether to include authentication header
- **Returns:** JSON string with `status_code` and `body`, or error message
- **Authentication:** Uses `LMS_API_KEY` from `.env.docker.secret`

### Path Security

Both file tools validate paths to prevent accessing files outside the project root:

```python
def validate_path(path: str) -> bool:
    """Ensure path doesn't escape project root."""
    if ".." in path or path.startswith("/"):
        return False
    resolved = (PROJECT_ROOT / path).resolve()
    return str(resolved).startswith(str(PROJECT_ROOT))
```

## Agentic Loop

The agentic loop enables the LLM to iteratively use tools to find answers:

1. **Initialize** conversation with system prompt and user question
2. **Call LLM** with tool schemas
3. **If tool calls returned:**
   - Execute each tool
   - Prevent duplicate file reads
   - Append results as `tool` role messages
   - Go to step 2
4. **If final answer returned:**
   - Extract source reference (wiki/ or backend/ paths)
   - Output JSON and exit
5. **Safety:** Stop after 10 tool calls

### System Prompt Strategy

The system prompt guides the LLM to choose the right tool:

- **Wiki questions**: Use `list_files("wiki")` first, then `read_file`
- **Source code questions**: Read files directly if path is known
- **API questions**: Use `query_api` to query data or check behavior
- **Bug diagnosis**: Query API to see error, then read source to find bug

The prompt emphasizes:
- Using tools instead of prior knowledge
- Being efficient with tool calls
- Including specific details from files in answers
- Including source references

## Environment Variables

| Variable | Source | Purpose |
|----------|--------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | LLM provider authentication |
| `LLM_API_BASE` | `.env.agent.secret` | LLM API endpoint |
| `LLM_MODEL` | `.env.agent.secret` | Model name |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | Environment or default | Backend API base URL (default: `http://localhost:42002`) |

## How to Run

### Prerequisites

1. **Set up environment files**:
   ```bash
   cp .env.agent.example .env.agent.secret
   # Ensure .env.docker.secret exists with LMS_API_KEY
   ```

2. **Configure credentials**:
   - `.env.agent.secret`: LLM API key, base URL, model
   - `.env.docker.secret`: Backend API key

3. **Install dependencies**:
   ```bash
   uv sync
   ```

### Usage

Run the agent with a question:

```bash
uv run agent.py "How do you resolve a merge conflict?"
uv run agent.py "What framework does the backend use?"
uv run agent.py "How many items are in the database?"
```

### Error Handling

- **Missing arguments**: Prints usage to stderr, exits with code 1
- **Missing environment variables**: Prints error to stderr, exits with code 1
- **API connection failure**: Returns error to LLM, which may retry or report
- **Invalid path**: Returns error message to LLM (doesn't crash)
- **Timeout**: 60-second limit enforced
- **Max tool calls**: Stops after 10 tool calls

## File Structure

```
se-toolkit-lab-6/
├── agent.py              # Main agent CLI with tools and agentic loop
├── AGENT.md              # This documentation
├── .env.agent.secret     # LLM credentials (gitignored)
├── .env.docker.secret    # Backend API credentials (gitignored)
├── plans/
│   ├── task-1.md         # Task 1: LLM call
│   ├── task-2.md         # Task 2: Documentation agent
│   └── task-3.md         # Task 3: System agent
├── tests/
│   └── test_agent.py     # 5 regression tests
└── pyproject.toml        # Project dependencies
```

## Dependencies

- `httpx`: Async HTTP client for API requests
- Standard library: `json`, `os`, `sys`, `asyncio`, `pathlib`, `re`

## Testing

Run all tests:
```bash
uv run pytest tests/test_agent.py -v
```

Run evaluation benchmark:
```bash
uv run run_eval.py
```

## Benchmark Results

| Iteration | Score | Key Fixes |
|-----------|-------|-----------|
| 1 | 5/10 | Initial implementation |
| 2 | 6/10 | Added `auth` parameter for unauthenticated API tests |
| 3 | 7/10 | Fixed source extraction for backend/ paths |
| 4 | 7/10 | Improved system prompt for efficiency |
| 5 | 10/10 | Increased content limits for source code |

## Lessons Learned

1. **Tool descriptions matter**: The LLM relies heavily on tool descriptions to decide when to use each tool. Adding specific guidance like "Set auth=false to test unauthenticated access" enabled the agent to pass question 6.

2. **Source extraction is tricky**: The `extract_source` function needed multiple iterations to capture wiki paths, backend paths, and generic file references. The final implementation uses regex patterns for `.md` and `.py` files.

3. **Content limits affect accuracy**: Source code files need sufficient context (8000+ chars) for the LLM to identify bugs. Initial truncation at 4000 chars caused the LLM to miss critical code sections.

4. **System prompt tuning**: The system prompt evolved through multiple iterations. Key additions included explicit guidance for bug diagnosis workflows and efficiency reminders to minimize unnecessary `list_files` calls.

5. **PowerShell argument handling**: Windows PowerShell splits quoted arguments differently than Unix shells. The fix was to join all `sys.argv[1:]` arguments and strip surrounding quotes.

6. **Duplicate prevention**: Without tracking which files were already read, the LLM would read the same file multiple times, wasting tool call budget. Adding a `files_read` set prevented this issue.

7. **Environment variable separation**: Keeping LLM credentials (`.env.agent.secret`) separate from backend API credentials (`.env.docker.secret`) is important for security and deployment flexibility.
