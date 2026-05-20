# Arquitectura de Lemoria

## Diagrama de arquitectura

```mermaid
graph TB
  USER([Usuario]) --> OC[OpenCode]

  subgraph OC[OpenCode]
    SKILL[Skill: lemoria] --> OA[Orchestrator Agent]
    OA -->|backend-agent| BA[Backend Agent]
    OA -->|db-agent| DA[DB Agent]
    OA -->|testing-agent| TA[Testing Agent]
    OA -->|github-agent| GA[GitHub Agent]
    OA -->|review-agent| RA[Review Agent]
    OA -->|documentation-agent| DOA[Documentation Agent]
  end

  subgraph LEMORIA[Lemoria System]
    CLI[lemoria CLI] --> CORE[Lemoria Core]
    CORE --> PS[Project Service]
    CORE --> MS[Memory Service]
    CORE --> ORCH[Orchestrator Service]
    CORE --> FE[Flow Engine]
    CORE --> VS[Vault Service]
    CORE --> GS[Git Service]
  end

  LEMORIA --> DB[(PostgreSQL)]
  VS --> OBSIDIAN[Obsidian Vault<br/>vault/obsidian/]
  GS --> GITHUB[GitHub]

  OC -.->|ejecuta comandos| CLI
  LEMORIA -->|lectura/escritura| DB
```

## Diagrama de flujo SDD

```mermaid
flowchart LR
  A[Idea] --> B[Spec]
  B --> C[PRD]
  C --> D[Tasks]
  D --> E[Architecture]
  E --> F[Implementation]
  F --> G[Testing]
  G --> H[Review]
  H --> I[Commit]
  I --> J[Push]
  J --> K[Documentation]
  K --> L[Memory Update]
  L -.->|feedback| A
```

## Diagrama de jerarquía de contexto

```mermaid
flowchart LR
  GC[Global Context] --> PC[Project Context]
  PC --> TC[Task Context]
  TC --> AC[Agent Context]
```

## Diagrama de entidades

```mermaid
erDiagram
  Project ||--o{ Conversation : has
  Project ||--o{ PRD : has
  Project ||--o{ Task : has
  Project ||--o{ Decision : has
  Project ||--o{ Context : has
  Project ||--o{ ErrorRecord : has

  Conversation ||--o{ Message : contains
  PRD ||--o{ Spec : "has specs"
  PRD ||--o{ Task : "generates tasks"

  Task ||--o{ Commit : "linked to"
  Task }o--|| Agent : "assigned to"

  Commit ||--o{ FileRecord : modifies
  Commit ||--|| Push : "pushed as"

  ErrorRecord ||--o| Solution : "has solution"

  Agent ||--o{ AgentExecution : executes
  Task ||--o{ AgentExecution : triggers
```

## Diagrama de componentes

```mermaid
graph RL
  subgraph APPS[Lemoria Apps]
    A1[agents/]
    A2[memory/]
    A3[projects/]
    A4[github/]
    A5[obsidian/]
    A6[orchestration/]
    A7[sdd/]
  end

  subgraph DB_LAYER[Database Layer]
    M1[models/]
    M2[migrations/]
    M3[seed/]
  end

  subgraph AGENTS[OpenCode Agents]
    AG1[orchestrator]
    AG2[backend-agent]
    AG3[db-agent]
    AG4[testing-agent]
    AG5[github-agent]
    AG6[review-agent]
    AG7[documentation-agent]
  end

  AGENTS -->|subagentes| AG1
  APPS -->|persiste| DB_LAYER
  DB_LAYER --> PostgreSQL
```

## Visión general

```
Usuario
  ↓
Lemoria Orchestrator
  ↓
Context Engine
  ↓
PostgreSQL
  ↓
Subagentes
  ↓
GitHub / Obsidian / Archivos
```

## Componentes

### Lemoria Core
Núcleo que inicia servicios, maneja configuración y administra proyectos.

### Lemoria Memory
Sistema de memoria persistente: conversaciones, PRDs, tareas, decisiones, errores, soluciones.

### Lemoria Orchestrator
Agente mayor que analiza contexto, revisa PRDs, delega tareas y consolida resultados.

### Lemoria Agents
Sistema multiagente especializado: backend, db, testing, documentation, github, review.

### Lemoria Flow
Motor SDD con flujo: Idea → Spec → PRD → Tasks → Architecture → Implementation → Testing → Review → Commit → Push → Documentation → Memory Update.

### Lemoria Vault
Integración con Obsidian para visualización humana y knowledge graph.

### Lemoria Git
Sistema de trazabilidad que registra commits, pushes, ramas y PRs vinculados a tareas.

## Jerarquía de contexto

```
Global Context
  ↓
Project Context
  ↓
Task Context
  ↓
Agent Context
```

Cada agente recibe únicamente el contexto necesario.

## Reglas fundamentales

1. El orquestador debe revisar contexto antes de delegar
2. Toda decisión importante debe registrarse
3. Todo cambio debe tener trazabilidad
4. Los agentes no modifican componentes críticos automáticamente
5. Priorizar contexto útil sobre memoria infinita
