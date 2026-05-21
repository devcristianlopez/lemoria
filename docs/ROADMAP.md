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
- [x] 7 subagentes especializados (backend, db, testing, github, review, documentation)
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

## Fase 4 — Obsidian Sync (funcionalidad básica)
- [x] Exportación a Markdown (vault service)
- [x] Vault configurable por proyecto
- [ ] Sincronización bidireccional (PostgreSQL ↔ Obsidian)
- [ ] Knowledge graph navegable
- [ ] Watch de cambios en vault

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
