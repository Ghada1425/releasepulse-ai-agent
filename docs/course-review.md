# Course review and attribution

Reviewed 29 October 2026:
- https://sdaiaacademy.github.io/agentic-ai/ (also inspected repository index.html)
- https://github.com/SDAIAAcademy/agentic-ai
- https://raw.githubusercontent.com/SDAIAAcademy/agentic-ai/main/labs/capstone/README.md
- `labs/capstone/starter.py`, `labs/evals.py`, `labs/servers/madar_mcp.py`
- Course commit: e950ba2f14b47deb6c30a586a6d4d5b77944e37d

Track 2 requires a domain harness with tools/MCP, context, permission controls, budgets, >=15 tasks in
two configurations, security analysis and an eight-minute presentation. The published weights are
25/25/20/20/10 for working system, context/harness, evaluation, security/operations, presentation.

The starter demonstrates bounded history, result caps, MCP stdio and explicit approval. The evaluation
framework uses JSONL task IDs and automatic tool/content graders. ReleasePulse follows these concepts
with an independently implemented typed policy grader and JSONL format, avoiding a dependency on the
Madar municipal database. No course source code, datasets or slides are redistributed.
No root license was found in the inspected course checkout, so course code was not copied or relicensed.
MIT covers only the original ReleasePulse code and original synthetic data. Third-party packages keep
their respective licenses. This independent academic project is not endorsed by SDAIA Academy.

