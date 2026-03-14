# Task 2: The Documentation Agent - Implementation Plan

## Overview

Extend the Task 1 agent with tools (`read_file`, `list_files`) and an agentic loop to answer questions by reading the project wiki.

## Tool Schemas

### Custom Schema Format

Define tools as Python functions with metadata for the LLM:

```python
TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file from the project repository",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path from project root"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_files",
        "description": "List files in a directory",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative directory path from project root"}
            },
            "required": ["path"]
        }
    }
]
```

Convert to LLM's function-calling format when making API requests.

## Tool Implementation

### `read_file(path)`

- Open and read file at `project_root / path`
- **Security**: Validate path doesn't contain `..` or start with `/`
- **Error handling**: Return error message if file doesn't exist

### `list_files(path)`

- List entries in `project_root / path` using `os.listdir()` or `pathlib`
- **Security**: Same path validation as `read_file`
- **Output**: Newline-separated list of filenames

### Path Security

```python
def validate_path(path: str) -> bool:
    """Ensure path doesn't escape project root."""
    if ".." in path or path.startswith("/"):
        return False
    resolved = (PROJECT_ROOT / path).resolve()
    return str(resolved).startswith(str(PROJECT_ROOT))
```

## Agentic Loop

### Message History Approach

Maintain a list of messages sent to the LLM:

1. **Initialize**: `messages = [system_prompt, user_question]`
2. **Loop**:
   - Call LLM with all messages
   - If LLM returns `tool_calls`:
     - Execute each tool
     - Append tool results as `{"role": "tool", "content": result}`
     - Continue loop
   - If LLM returns text answer:
     - Extract answer and source
     - Output JSON and exit
3. **Safety**: Stop after 10 tool calls

### Message Format

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": "How do you resolve a merge conflict?"},
    {"role": "assistant", "content": None, "tool_calls": [...]},
    {"role": "tool", "content": "file contents...", "tool_call_id": "..."},
    {"role": "assistant", "content": "Based on the file..."},
]
```

## System Prompt Strategy

The system prompt should instruct the LLM to:

1. Use `list_files` to discover wiki files
2. Use `read_file` to read relevant files
3. Include source references (file path + section anchor) in the answer
4. Call tools step by step, not all at once

Example:
```
You are a documentation assistant. You have access to tools to read files and list directories.

When answering questions:
1. First use list_files to explore the wiki directory
2. Then use read_file to read relevant files
3. Find the answer and include the source as "wiki/filename.md#section-anchor"
4. Only call one tool at a time

Always include the source reference in your final answer.
```

## Output Format

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

## Error Handling

- **Invalid path**: Return error message to LLM, let it decide next step
- **File not found**: Return error message to LLM
- **LLM doesn't call tools**: Use the answer as-is, set source to empty string
- **Timeout**: Exit with error after 60 seconds

## Testing Strategy

Two regression tests:

1. **Test merge conflict question**:
   - Question: `"How do you resolve a merge conflict?"`
   - Expected: `read_file` in tool_calls, `wiki/git-workflow.md` in source

2. **Test list_files question**:
   - Question: `"What files are in the wiki?"`
   - Expected: `list_files` in tool_calls

## Dependencies

- No new dependencies needed (use `os`, `pathlib` from stdlib)
