"""Regression tests for agent.py.

These tests run agent.py as a subprocess and verify the JSON output structure.
"""

import json
import subprocess
import sys


def test_agent_output_structure():
    """Test that agent.py outputs valid JSON with required fields.
    
    Runs agent.py with a simple question and checks:
    - Exit code is 0
    - Output is valid JSON
    - 'answer' field is present and is a string
    - 'tool_calls' field is present and is an array
    """
    # Run agent.py as a subprocess
    result = subprocess.run(
        [sys.executable, "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"
    
    # Check output is not empty
    assert result.stdout.strip(), "Agent produced no output"
    
    # Parse JSON
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e
    
    # Check required fields
    assert "answer" in data, "Missing 'answer' field in output"
    assert isinstance(data["answer"], str), "'answer' field must be a string"
    assert len(data["answer"]) > 0, "'answer' field is empty"
    
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' field must be an array"


def test_agent_merge_conflict_question():
    """Test that agent uses read_file for merge conflict question.
    
    Question: "How do you resolve a merge conflict?"
    Expected:
    - read_file in tool_calls
    - wiki/git.md or wiki/git-vscode.md in source (where merge conflict info is)
    """
    result = subprocess.run(
        [sys.executable, "agent.py", "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"
    
    # Parse JSON
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e
    
    # Check required fields
    assert "answer" in data, "Missing 'answer' field in output"
    assert "source" in data, "Missing 'source' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    
    # Check that read_file was used
    tools_used = [tc.get("tool") for tc in data["tool_calls"]]
    assert "read_file" in tools_used, f"Expected 'read_file' in tool_calls, got: {tools_used}"
    
    # Check that source contains git-related file (git.md or git-vscode.md has merge conflict info)
    source = data.get("source", "")
    assert any(x in source for x in ["wiki/git.md", "wiki/git-vscode.md"]), f"Expected git-related file in source, got: {source}"


def test_agent_list_files_question():
    """Test that agent uses list_files for wiki directory question.
    
    Question: "What files are in the wiki directory?"
    Expected:
    - list_files in tool_calls
    """
    result = subprocess.run(
        [sys.executable, "agent.py", "What files are in the wiki directory?"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"
    
    # Parse JSON
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e
    
    # Check required fields
    assert "answer" in data, "Missing 'answer' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    
    # Check that list_files was used
    tools_used = [tc.get("tool") for tc in data["tool_calls"]]
    assert "list_files" in tools_used, f"Expected 'list_files' in tool_calls, got: {tools_used}"


if __name__ == "__main__":
    test_agent_output_structure()
    test_agent_merge_conflict_question()
    test_agent_list_files_question()
    print("All tests passed!")
