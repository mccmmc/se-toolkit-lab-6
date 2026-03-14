Call an LLM from Code
Build a CLI that connects to an LLM and answers questions. This is the foundation for the agent you will build in the next tasks.

What you will build
A Python CLI program (agent.py) that takes a question, sends it to an LLM, and returns a structured JSON answer. No tools or agentic loop yet — just the basic plumbing: parse input, call the LLM, format output. You will add tools and the agentic loop in Tasks 2–3.

User question → agent.py → LLM API → JSON answer
Input — a question as the first command-line argument:

uv run agent.py "What does REST stand for?"
Output — a single JSON line to stdout:

{"answer": "Representational State Transfer.", "tool_calls": []}
Rules:

answer and tool_calls fields are required in the output.
tool_calls is an empty array for this task (you will populate it in Task 2).
Only valid JSON goes to stdout. All debug/progress output goes to stderr.
The agent must respond within 60 seconds.
Exit code 0 on success.
How to get access to an LLM?
Your agent needs an LLM that supports the OpenAI-compatible chat completions API. You are free to use any provider.

Recommended: Set up the Qwen Code API on your VM

Qwen Code provides 1000 free requests per day, works from Russia, and requires no credit card.

Follow the setup instructions to deploy it on your VM.

Model	Tool calling	Notes
qwen3-coder-plus	Strong	Recommended, default in .env.agent.example
coder-model	Strong	Qwen 3.5 Plus
Alternative: OpenRouter (click to open)
Create the agent environment file:

cp .env.agent.example .env.agent.secret
Edit .env.agent.secret and fill in LLM_API_KEY, LLM_API_BASE, and LLM_MODEL. Your agent reads from this file.

Note: This is not the same as LMS_API_KEY in .env.docker.secret. That one protects your backend LMS endpoints. LLM_API_KEY authenticates with your LLM provider.