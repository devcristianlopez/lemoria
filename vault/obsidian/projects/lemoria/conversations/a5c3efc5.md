# Conversación: Refactor: agents and skills to generic + English, Context7 setup
**Proyecto**: [[projects/lemoria/README|lemoria]]
**Created**: 2026-06-26 19:26:56.229660+00:00

## user

Refactor all agents to be generic and language-agnostic in English. Create frontend-agent (new). Create 7 skills: frontend, backend, database, testing, code-review, git-workflow, documentation. Install Context7 MCP for real-time library docs. Integrate Context7 into lemoria installation.
## agent

Refactored 8 agents to generic + English (orchestrator, implementation-agent, frontend-agent, db-agent, testing-agent, review-agent, github-agent, documentation-agent). Created 7 skills (frontend, backend, database, testing, code-review, git-workflow, documentation). Installed Context7 MCP. Updated install.sh and INSTALL.md. All synced to global (~/.config/opencode/) and project (.opencode/) levels.
## user

Mejorar el orquestador para que siempre documente y commitee. Hoy a veces salta esos pasos.
## agent

Orchestrator mejorado: workflow expandido a 13 pasos con commit y document obligatorios, closing checklist de 6 puntos, documentation-agent actualizado con vault sync y tabla de qué documentar según el cambio, github-agent con detección de cambios sin commit

---
Volver a [[projects/lemoria/README|lemoria]]
