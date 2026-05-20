---
name: lemoria
description: >-
  Use when the user mentions lemoria or wants to create/manage projects,
  start SDD flows, register agents, or interact with Lemoria's memory system.
  Covers project init, conversation management, task tracking, and Obsidian sync.
---

# Lemoria Skill

Lemoria is a memory & orchestration OS for AI-assisted development.
It runs as a global CLI command and uses PostgreSQL for persistent storage.

## Quick commands

```bash
lemoria init                          # Initialize DB + vault
lemoria project create "name" -d ".." # Create project
lemoria project list                  # List projects
lemoria conv create <pid> -t "title"  # Start conversation
lemoria conv add <cid> user "msg"     # Add message
lemoria agent register name role -d.. # Register agent
lemoria agent list                    # List agents
lemoria flow start <pid> "idea"       # Start SDD flow
```

## Architecture

- PostgreSQL is source of truth (Docker)
- Obsidian vault at vault/obsidian/ (visual representation)
- Agents in .opencode/agents/
- Each agent receives only the context it needs

## Agent workflow

1. Orchestrator analyzes context and PRDs
2. Delegates to specialized subagents
3. Subagents report back
4. Results stored in memory
5. Vault synced to Obsidian
