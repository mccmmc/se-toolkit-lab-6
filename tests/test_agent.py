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


if __name__ == "__main__":
    test_agent_output_structure()
    print("All tests passed!")
