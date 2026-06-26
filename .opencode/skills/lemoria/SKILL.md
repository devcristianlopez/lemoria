---
name: lemoria
description: >-
  Use for ANY software development task: feature requests, bug fixes, code
  implementation, refactoring, testing, documentation, commits, project setup.
  Also when the user explicitly mentions lemoria, SDD, PRD, or agents.
  This is the default orchestrator for all development work.
---

# Lemoria — Orchestration & Memory System

## Full workflow (SDD)

When the user requests any feature or technical change, the orchestrator executes:

```
User request
  ↓
1. lemoria project list → create project if not exists
2. lemoria conv create → start conversation
3. lemoria conv add user → log request
4. lemoria flow start → create PRD
5. lemoria task create → decompose into tasks
6. Delegate to subagents (@implementation-agent, @testing-agent, etc.)
7. Consolidate results → lemoria conv add agent
8. lemoria decision log → register decisions
```

## CLI commands

```bash
# Projects
lemoria project create "name" -d "desc"
lemoria project list

# Conversations
lemoria conv create <pid> -t "title"
lemoria conv add <cid> user "msg"
lemoria conv add <cid> agent "msg"

# PRDs
lemoria flow start <pid> "idea"

# Tasks
lemoria task create <pid> <prd-id> --title "task"
lemoria task list <pid>

# Decisions
lemoria decision log <pid> -t "title" -d "desc"

# Agents
lemoria agent list
```

## Available agents

| Agent | Role | Permissions |
|-------|------|-------------|
| orchestrator | Orchestrator (default) | bash allow, edit deny |
| implementation-agent | Implementation | bash+edit allow |
| db-agent | Database | bash+edit allow |
| testing-agent | Testing | bash+edit allow |
| github-agent | Traceability | bash allow, edit deny |
| review-agent | Review | all deny |
| documentation-agent | Documentation | bash+edit allow |

## Context

- PostgreSQL is the source of truth
- Obsidian vault is the visual representation
- Each agent receives only the context it needs
