# Agent Architecture

## Overview

This project implements a CLI agent (`agent.py`) that connects to an LLM and returns structured JSON answers. The agent has tools (`read_file`, `list_files`) to navigate the project wiki and an agentic loop to iteratively find answers.

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
   - Reads `.env.agent.secret` in the project root
   - Loads `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
   - Only sets environment variables if not already defined

2. **Configuration Validation** (`get_llm_config()`)
   - Validates that all required environment variables are present
   - Exits with error code 1 if any are missing

3. **Tools**
   - `read_file(path)`: Read a file from the project repository
   - `list_files(path)`: List files in a directory
   - Both tools validate paths to prevent directory traversal attacks

4. **LLM API Call** (`call_ll()`)
   - Sends async HTTP POST to `{LLM_API_BASE}/chat/completions`
   - Uses `httpx` for async HTTP requests
   - Supports tool schemas for function calling
   - 60-second timeout

5. **Agentic Loop** (`run_agentic_loop()`)
   - Maintains conversation history with the LLM
   - Executes tool calls and feeds results back
   - Stops after 10 tool calls or when LLM provides final answer
   - Extracts source reference from the answer

6. **Main Entry Point** (`main()`)
   - Parses command-line argument (the question)
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
- `source` (string): Reference to the wiki file/section used
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

### Path Security

Both tools validate paths to prevent accessing files outside the project root:

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
   - Append results as `tool` role messages
   - Go to step 2
4. **If final answer returned:**
   - Extract source reference
   - Output JSON and exit
5. **Safety:** Stop after 10 tool calls

### System Prompt

The system prompt instructs the LLM to:
- Use tools to find answers (not rely on prior knowledge)
- Start with `list_files` to discover relevant files
- Use `read_file` to read specific files
- Include source references in the answer
- Call one tool at a time

## How to Run

### Prerequisites

1. **Set up the environment file**:
   ```bash
   cp .env.agent.example .env.agent.secret
   ```

2. **Configure your LLM credentials** in `.env.agent.secret`:
   - `LLM_API_KEY`: Your Qwen Code API key
   - `LLM_API_BASE`: Your VM's API endpoint (e.g., `http://<vm-ip>:<port>/v1`)
   - `LLM_MODEL`: Model name (e.g., `qwen3-coder-plus`)

3. **Install dependencies** (handled by `uv`):
   ```bash
   uv sync
   ```

### Usage

Run the agent with a question as the command-line argument:

```bash
uv run agent.py "How do you resolve a merge conflict?"
```

Example output:
```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [...]
}
```

### Error Handling

- **Missing arguments**: Prints usage to stderr, exits with code 1
- **Missing environment variables**: Prints error to stderr, exits with code 1
- **API connection failure**: Prints error to stderr, exits with code 1
- **Invalid path**: Returns error message to LLM (doesn't crash)
- **Timeout**: The subprocess runner enforces a 60-second timeout
- **Max tool calls**: Stops after 10 tool calls

## File Structure

```
se-toolkit-lab-6/
├── agent.py              # Main agent CLI with tools and agentic loop
├── AGENT.md              # This documentation
├── .env.agent.secret     # LLM credentials (gitignored)
├── .env.agent.example    # Example environment file
├── plans/
│   ├── task-1.md         # Task 1 implementation plan
│   └── task-2.md         # Task 2 implementation plan
├── tests/
│   └── test_agent.py     # Regression tests
└── pyproject.toml        # Project dependencies
```

## Dependencies

- `httpx`: Async HTTP client for API requests
- Standard library: `json`, `os`, `sys`, `asyncio`, `pathlib`, `re`

## Testing

Run the agent manually:
```bash
uv run agent.py "What is 2+2?"
uv run agent.py "How do you resolve a merge conflict?"
```

Run tests:
```bash
uv run pytest tests/test_agent.py -v
```

Run the evaluation script (requires autochecker credentials):
```bash
uv run run_eval.py --index 0
```
