---
name: lemoria
description: >-
  Use for ANY software development task: feature requests, bug fixes, code
  implementation, refactoring, testing, documentation, commits, project setup.
  Also when the user explicitly mentions lemoria, SDD, PRD, or agents.
  This is the default orchestrator for all development work.
---

# Lemoria — Sistema de Orquestación y Memoria

## Workflow completo (SDD)

Cuando el usuario pide cualquier feature o cambio técnico, el orquestador ejecuta:

```
User request
  ↓
1. lemoria project list → crear proyecto si no existe
2. lemoria conv create → iniciar conversación
3. lemoria conv add user → registrar pedido
4. lemoria flow start → crear PRD
5. lemoria task create → desglosar en tareas
6. Delegar a subagentes (@backend-agent, @testing-agent, etc.)
7. Consolidar resultados → lemoria conv add agent
8. lemoria decision log → registrar decisiones
```

## Comandos CLI

```bash
# Proyectos
lemoria project create "name" -d "desc"
lemoria project list

# Conversaciones
lemoria conv create <pid> -t "title"
lemoria conv add <cid> user "msg"
lemoria conv add <cid> agent "msg"

# PRDs
lemoria flow start <pid> "idea"

# Tareas
lemoria task create <pid> <prd-id> --title "tarea"
lemoria task list <pid>

# Decisiones
lemoria decision log <pid> -t "title" -d "desc"

# Agentes
lemoria agent list
```

## Agentes disponibles

| Agente | Rol | Permisos |
|--------|-----|----------|
| orchestrator | Orquestador (default) | bash allow, edit deny |
| backend-agent | Implementación | bash+edit allow |
| db-agent | Base de datos | bash+edit allow |
| testing-agent | Tests | bash+edit allow |
| github-agent | Trazabilidad | bash allow, edit deny |
| review-agent | Revisión | todo deny |
| documentation-agent | Documentación | bash+edit allow |

## Contexto

- PostgreSQL es fuente de verdad
- Obsidian vault es representación visual
- Cada agente recibe solo el contexto necesario
