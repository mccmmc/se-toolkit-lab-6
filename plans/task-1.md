# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider and Model

- **Provider**: Qwen Code API (OpenAI-compatible endpoint)
- **Model**: `qwen3-coder-plus`
- **API Base**: Configured via `LLM_API_BASE` environment variable
- **API Key**: Stored in `.env.agent.secret` (not hardcoded)

## Agent Architecture

### Input/Output Flow

```
Command line argument → agent.py → HTTP POST to LLM API → Parse response → JSON to stdout
```

### Components

1. **Environment Loading**: Read `.env.agent.secret` to get `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
2. **Argument Parsing**: Get the question from `sys.argv[1]`
3. **API Call**: Send POST request to `{LLM_API_BASE}/chat/completions` with the question
4. **Response Parsing**: Extract the assistant's message from the LLM response
5. **JSON Output**: Print `{"answer": "...", "tool_calls": []}` to stdout

### Error Handling

- Missing arguments → print usage to stderr, exit code 1
- Missing environment variables → print error to stderr, exit code 1
- API request failure → print error to stderr, exit code 1
- Timeout (60s) → handled by subprocess runner

### Output Rules

- **stdout**: Only valid JSON with `answer` and `tool_calls` fields
- **stderr**: All debug/progress messages
- **Exit code**: 0 on success, non-zero on error

## Dependencies

- Use `httpx` (already in `pyproject.toml`) for async HTTP requests
- Use `os.environ` for environment variables
- Use `json` for JSON parsing/output
- Use `sys` for command-line arguments and stderr

## Testing Strategy

- Run `uv run agent.py "What is 2+2?"` and verify JSON output
- Check that `answer` field contains a response
- Check that `tool_calls` is an empty array
