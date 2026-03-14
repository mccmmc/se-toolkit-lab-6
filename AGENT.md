# Agent Architecture

## Overview

This project implements a CLI agent (`agent.py`) that connects to an LLM and returns structured JSON answers. The agent serves as the foundation for more advanced features (tools, agentic loop) in subsequent tasks.

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
HTTP POST to LLM API (/chat/completions)
    ↓
Parse LLM response
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

3. **LLM API Call** (`call_ll()`)
   - Sends async HTTP POST to `{LLM_API_BASE}/chat/completions`
   - Uses `httpx` for async HTTP requests
   - Includes system prompt and user question in the request
   - 60-second timeout

4. **Main Entry Point** (`main()`)
   - Parses command-line argument (the question)
   - Orchestrates the flow
   - Outputs JSON to stdout
   - All debug output goes to stderr

### Output Format

The agent outputs a single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

- `answer` (string): The LLM's response to the question
- `tool_calls` (array): Empty for Task 1, populated in Task 2+

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
uv run agent.py "What does REST stand for?"
```

Example output:
```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Error Handling

- **Missing arguments**: Prints usage to stderr, exits with code 1
- **Missing environment variables**: Prints error to stderr, exits with code 1
- **API connection failure**: Prints error to stderr, exits with code 1
- **Timeout**: The subprocess runner enforces a 60-second timeout

## File Structure

```
se-toolkit-lab-6/
├── agent.py              # Main agent CLI
├── AGENT.md              # This documentation
├── .env.agent.secret     # LLM credentials (gitignored)
├── .env.agent.example    # Example environment file
├── plans/
│   └── task-1.md         # Implementation plan
└── pyproject.toml        # Project dependencies
```

## Dependencies

- `httpx`: Async HTTP client for API requests
- Standard library: `json`, `os`, `sys`, `asyncio`, `pathlib`

## Testing

Run the agent manually:
```bash
uv run agent.py "What is 2+2?"
```

Run the evaluation script (requires autochecker credentials):
```bash
uv run run_eval.py --index 0
```
