# Arquitectura de Lemoria

## Diagrama de arquitectura

```mermaid
graph TB
  USER([Usuario]) --> OC[OpenCode]

  subgraph OC[OpenCode]
    SKILL[Skill: lemoria] --> OA[Orchestrator Agent]
    OA -->|implementation-agent| IA[Implementation Agent]
    OA -->|frontend-agent| FA[Frontend Agent]
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

## Diagrama de flujo SDD con State Machine

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

  subgraph SM[State Machine - flow_steps]
    S1[flow step<br/>--status running] --> S2[Implementación]
    S2 --> S3[flow step<br/>--status completed]
    S3 --> S4[flow status<br/>verifica avance]
  end
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
  PRD ||--o{ FlowStep : "tracks steps"

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
    AG2[implementation-agent]
    AG3[frontend-agent]
    AG4[db-agent]
    AG5[testing-agent]
    AG6[github-agent]
    AG7[review-agent]
    AG8[documentation-agent]
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
Sistema multiagente especializado: implementation, frontend, db, testing, github, review, documentation.

### Lemoria Vault
Integración bidireccional con Obsidian: exporta entidades a markdown con frontmatter (`vault sync`) y reconstruye la DB desde las notas (`vault restore`).

### Lemoria Flow
Motor SDD con state machine. Cada paso del flujo se persiste en `flow_steps` con `flow_id`, `step`, `status`, `started_at`, `completed_at`, `output`. Permite reanudar flujos interrumpidos y ver el progreso completo.

### Lemoria Git
Sistema de trazabilidad que registra commits, pushes, ramas y PRs vinculados a tareas.

### Enums y CheckConstraints
8 enums tipados (`PRDStatus`, `TaskStatus`, `FlowStepStatus`, `DecisionStatus`, `ExecutionStatus`, `SpecStatus`, `CommitFileStatus`, `SolutionOutcome`) con `CheckConstraint` en 7 modelos para integridad de datos a nivel DB.

### Context7 MCP Server
Servidor MCP remoto para consultar documentación en tiempo real de librerías y frameworks. Configurado en `~/.config/opencode/opencode.json`.

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
2. Toda decisión importante debe registrarse como ADR
3. Todo cambio debe tener trazabilidad (tarea → commit → push)
4. Todo paso del flujo se persiste como flow step en la DB
5. Commit y Documentation son pasos obligatorios (no se pueden saltar)
6. Los agentes no modifican componentes críticos automáticamente
7. Priorizar contexto útil sobre memoria infinita
