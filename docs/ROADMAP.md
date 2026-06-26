# Roadmap

## Fase 1 — Core Memory (completada)
- [x] PostgreSQL (Docker)
- [x] Proyectos (CRUD)
- [x] Conversaciones y mensajes
- [x] PRDs y specs
- [x] Tareas (create, list, status)
- [x] Decisiones técnicas (ADR log)
- [x] Contexto jerárquico (global → project → task → agent)
- [x] Errores y soluciones

## Fase 2 — Orquestación (completada)
- [x] Agente mayor/orquestador (modo primary, default_agent)
- [x] 8 subagentes especializados (implementation, frontend, db, testing, github, review, documentation)
- [x] Delegación con contexto mínimo
- [x] Flujo SDD completo (idea → memory update)
- [x] CLI con Click (project, conv, flow, task, decision, agent)
- [x] Instalación global (pip install --user)
- [x] Mejores prácticas por agente (SOLID, FIRST, Diátaxis, etc.)

## Fase 3 — GitHub Intelligence (completada)
- [x] Registro de commits vinculados a tareas
- [x] Registro de pushes con PRs
- [x] Archivos modificados por commit
- [x] github-agent con detección de gh CLI
- [x] Conventional commits
- [x] GitHub Flow (branch strategy)

## Fase 4 — Obsidian Sync (completada)
- [x] Exportación a Markdown (vault service)
- [x] Vault configurable por proyecto
- [x] Sincronización bidireccional (PostgreSQL ↔ Obsidian) — `vault restore` reconstruye DB desde markdown
- [x] Knowledge graph navegable — decisiones, flow steps, PRDs exportados con wikilinks + frontmatter
- [ ] Watch de cambios en vault (pendiente)

## Fase 4.5 — Ingeniería de Calidad (completada)
- [x] 8 enums tipados con CheckConstraints en 7 modelos (integridad a nivel DB)
- [x] 41 tests automatizados (pytest, SQLite in-memory)
- [x] CI en GitHub Actions (matrix Python 3.11/3.12/3.13, PostgreSQL, ruff, Codecov)
- [x] FlowStep state machine (flow step CLI + orquestador resumible)
- [x] CLI completo: spec, error, context commands
- [x] Agentes refactorizados a inglés genérico (implementation-agent, frontend-agent)
- [x] 7 skills modulares (frontend, backend, database, testing, code-review, git-workflow, documentation)
- [x] Context7 MCP server para documentación en tiempo real
- [x] Instalador actualizado con Context7 opcional + 8 skills

## Fase 5 — Semantic Memory (pendiente)
- [ ] pgvector extension
- [ ] Embeddings (generación y almacenamiento)
- [ ] Búsqueda semántica sobre memoria
- [ ] RAG (Retrieval Augmented Generation)
- [ ] Recomendación de contexto relevante

## Fase 6 — Multi-proyecto y colaboración (futuro)
- [ ] Templates de proyecto
- [ ] Import/export de memoria
- [ ] Múltiples desarrolladores
- [ ] Lemoria server mode
