#!/usr/bin/env python3
"""Agent CLI with tools and agentic loop.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
    All debug output goes to stderr.
"""

import json
import os
import sys
from pathlib import Path

import httpx

# Project root for tool security
PROJECT_ROOT = Path(__file__).parent.resolve()

# Maximum tool calls per question
MAX_TOOL_CALLS = 10


def load_env() -> None:
    """Load environment variables from .env.agent.secret."""
    env_file = Path(".env.agent.secret")
    if not env_file.exists():
        print(f"Error: {env_file} not found", file=sys.stderr)
        print("Copy .env.agent.example to .env.agent.secret and fill in your credentials", file=sys.stderr)
        sys.exit(1)

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_llm_config() -> tuple[str, str, str]:
    """Get LLM configuration from environment variables."""
    api_key = os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("LLM_API_BASE")
    model = os.environ.get("LLM_MODEL")

    if not api_key:
        print("Error: LLM_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    if not api_base:
        print("Error: LLM_API_BASE not set", file=sys.stderr)
        sys.exit(1)
    if not model:
        print("Error: LLM_MODEL not set", file=sys.stderr)
        sys.exit(1)

    return api_key, api_base, model


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def validate_path(path: str) -> bool:
    """Ensure path doesn't escape project root."""
    if ".." in path or path.startswith("/"):
        return False
    try:
        resolved = (PROJECT_ROOT / path).resolve()
        return str(resolved).startswith(str(PROJECT_ROOT))
    except Exception:
        return False


def read_file(path: str) -> str:
    """Read a file from the project repository.
    
    Args:
        path: Relative path from project root.
    
    Returns:
        File contents as string, or error message.
    """
    if not validate_path(path):
        return f"Error: Invalid path '{path}' - path traversal not allowed"
    
    file_path = PROJECT_ROOT / path
    if not file_path.exists():
        return f"Error: File not found: {path}"
    
    if not file_path.is_file():
        return f"Error: Not a file: {path}"
    
    try:
        return file_path.read_text()
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """List files and directories at a given path.
    
    Args:
        path: Relative directory path from project root.
    
    Returns:
        Newline-separated listing of entries, or error message.
    """
    if not validate_path(path):
        return f"Error: Invalid path '{path}' - path traversal not allowed"
    
    dir_path = PROJECT_ROOT / path
    if not dir_path.exists():
        return f"Error: Directory not found: {path}"
    
    if not dir_path.is_dir():
        return f"Error: Not a directory: {path}"
    
    try:
        entries = sorted([e.name for e in dir_path.iterdir()])
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory: {e}"


# Tool registry
TOOLS = {
    "read_file": {
        "description": "Read a file from the project repository",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path from project root"}
            },
            "required": ["path"]
        },
        "function": read_file,
    },
    "list_files": {
        "description": "List files and directories at a given path",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative directory path from project root"}
            },
            "required": ["path"]
        },
        "function": list_files,
    },
}


def get_tool_schemas() -> list[dict]:
    """Get tool schemas in OpenAI-compatible format."""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
        }
        for name, tool in TOOLS.items()
    ]


def execute_tool(tool_name: str, args: dict) -> str:
    """Execute a tool and return the result.
    
    Args:
        tool_name: Name of the tool to execute.
        args: Arguments for the tool.
    
    Returns:
        Tool result as string.
    """
    if tool_name not in TOOLS:
        return f"Error: Unknown tool '{tool_name}'"
    
    tool = TOOLS[tool_name]
    func = tool["function"]
    
    try:
        return func(**args)
    except Exception as e:
        return f"Error executing tool: {e}"


# ---------------------------------------------------------------------------
# LLM Communication
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a documentation assistant with access to tools. You MUST use tools to answer questions about the project.

Available tools:
- list_files(path): List files in a directory
- read_file(path): Read contents of a file

Rules:
1. You MUST use tools to find answers - do not rely on your prior knowledge
2. Start by using list_files("wiki") to see what documentation exists
3. Look for relevant files based on the question topic:
   - For git/merge conflicts: check git-workflow.md, git.md
   - For installation: check README.md, installation.md
   - For API: check api.md, rest-api.md
4. Use read_file to read specific files
5. Include source references like "wiki/filename.md#section-anchor" in your answer
6. Call one tool at a time and wait for results
7. Do NOT read the same file twice - if you already read a file, use the information you got

IMPORTANT: For any question about project documentation, you MUST call tools.
Do not answer from your prior knowledge - always use tools first.
If you cannot find the answer after reading relevant files, say so honestly.
"""


async def call_ll(
    messages: list[dict],
    api_key: str,
    api_base: str,
    model: str,
    tools: list[dict] | None = None,
) -> dict:
    """Call the LLM API and return the response.
    
    Args:
        messages: List of message dicts for the conversation.
        api_key: API key for authentication.
        api_base: Base URL for the API.
        model: Model name to use.
        tools: Optional list of tool schemas.
    
    Returns:
        The LLM response dict.
    """
    url = f"{api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "model": model,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"  # Let model decide when to call tools
        # For Qwen models, also try parallel_tool_calls
        payload["parallel_tool_calls"] = False

    print(f"Sending request to LLM with {len(messages)} messages", file=sys.stderr)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data


# ---------------------------------------------------------------------------
# Agentic Loop
# ---------------------------------------------------------------------------

async def run_agentic_loop(
    question: str,
    api_key: str,
    api_base: str,
    model: str,
) -> tuple[str, str, list[dict]]:
    """Run the agentic loop to answer a question.

    Args:
        question: The user's question.
        api_key: API key for authentication.
        api_base: Base URL for the API.
        model: Model name to use.

    Returns:
        Tuple of (answer, source, tool_calls).
    """
    # Initialize conversation
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_calls_log = []
    tool_call_count = 0
    tool_schemas = get_tool_schemas()
    files_read = set()  # Track which files have been read

    while tool_call_count < MAX_TOOL_CALLS:
        print(f"Loop iteration {tool_call_count + 1}, calling LLM...", file=sys.stderr)

        # Call LLM
        response = await call_ll(messages, api_key, api_base, model, tools=tool_schemas)
        choice = response["choices"][0]
        message = choice["message"]

        # Check for tool calls
        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            # LLM gave final answer
            print("LLM provided final answer", file=sys.stderr)
            answer = message.get("content", "")

            # Extract source from answer (look for wiki/... pattern)
            source = extract_source(answer)
            
            # If no source extracted, try to get it from tool calls
            if not source and tool_calls_log:
                for tc in tool_calls_log:
                    if tc["tool"] == "read_file":
                        path = tc["args"].get("path", "")
                        if path.startswith("wiki/"):
                            source = path
                            break

            return answer, source, tool_calls_log

        # First, add assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        })

        # Then execute tool calls and add responses
        for tool_call in tool_calls:
            tool_call_count += 1
            if tool_call_count > MAX_TOOL_CALLS:
                print(f"Reached max tool calls ({MAX_TOOL_CALLS})", file=sys.stderr)
                break

            tool_id = tool_call["id"]
            function = tool_call["function"]
            tool_name = function["name"]

            try:
                args = json.loads(function["arguments"])
            except json.JSONDecodeError:
                args = {}

            # Prevent reading the same file twice
            if tool_name == "read_file":
                path = args.get("path", "")
                if path in files_read:
                    print(f"Skipping duplicate read of {path}", file=sys.stderr)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": f"Already read this file. Use the information you have.",
                    })
                    tool_calls_log.append({
                        "tool": tool_name,
                        "args": args,
                        "result": "Already read this file.",
                    })
                    continue
                files_read.add(path)

            print(f"Executing tool: {tool_name} with args: {args}", file=sys.stderr)

            # Execute tool
            result = execute_tool(tool_name, args)

            # Log tool call
            tool_calls_log.append({
                "tool": tool_name,
                "args": args,
                "result": result[:500] if len(result) > 500 else result,  # Truncate long results
            })

            # Add tool response to messages (truncate for API)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": result[:4000] if len(result) > 4000 else result,  # Limit content size
            })
    
    # Reached max tool calls, use whatever answer we have
    print("Reached max tool calls, returning partial answer", file=sys.stderr)
    
    # Try to get an answer from the last message
    if messages and messages[-1].get("role") == "assistant":
        answer = messages[-1].get("content", "I reached the maximum number of tool calls.")
    else:
        answer = "I reached the maximum number of tool calls without finding a complete answer."
    
    source = extract_source(answer)
    return answer, source, tool_calls_log


def extract_source(answer: str) -> str:
    """Extract source reference from the answer.
    
    Looks for patterns like wiki/filename.md or wiki/filename.md#section
    
    Args:
        answer: The LLM's answer text.
    
    Returns:
        Source reference string, or empty if not found.
    """
    import re
    
    # Look for wiki/... pattern
    match = re.search(r'(wiki/[\w\-/]+\.md(?:#[\w\-]+)?)', answer)
    if match:
        return match.group(1)
    
    return ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point."""
    # Check command-line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    # Join all arguments to handle PowerShell quoting issues
    question = " ".join(sys.argv[1:])
    # Strip surrounding quotes if present (PowerShell sometimes includes them)
    if question.startswith('"') and question.endswith('"'):
        question = question[1:-1]
    elif question.startswith("'") and question.endswith("'"):
        question = question[1:-1]

    # Load environment and get configuration
    load_env()
    api_key, api_base, model = get_llm_config()

    print(f"Calling LLM with model: {model}", file=sys.stderr)

    # Run agentic loop
    import asyncio
    answer, source, tool_calls = asyncio.run(run_agentic_loop(question, api_key, api_base, model))

    print(f"Answer: {answer[:100]}...", file=sys.stderr)
    if source:
        print(f"Source: {source}", file=sys.stderr)

    # Output JSON to stdout
    result = {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
