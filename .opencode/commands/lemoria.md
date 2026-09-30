---
description: Start the Lemoria SDD orchestrator workflow for this request.
agent: build
model: openai/gpt-5.5
---

You are running the Lemoria SDD workflow from opencode.

Use the Lemoria project conventions and agent handoff model:
- Route development work through the orchestrator.
- Ask for or infer the relevant project, PRD, conversation, and task IDs when needed.
- Select the appropriate specialized agent for implementation, testing, database, frontend, documentation, git, or review work.
- Apply the requested model/effort expectations explicitly when delegating.
- Preserve existing repository and user configuration unless the user explicitly asks to change it.

User request:
$ARGUMENTS
