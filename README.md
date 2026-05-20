# Lemoria

**Sistema Operativo de Memoria y Orquestación para Desarrollo con IA**

Lemoria es una plataforma **local-first** que resuelve la pérdida de contexto en el desarrollo asistido por IA. Proporciona memoria persistente, coordinación multiagente, trazabilidad técnica y un flujo de desarrollo guiado por especificaciones (SDD).

```
Usuario → Orchestrator → Context Engine → PostgreSQL → Subagentes → GitHub / Obsidian / Archivos
```

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11+ / SQLAlchemy 2.0 |
| Base de Datos | PostgreSQL 16 (Docker) |
| ORM | SQLAlchemy + Alembic |
| Agentes | OpenCode (7 agentes) |
| CLI | Click |
| Vault | Obsidian (opcional) |
| Versionado | Git + GitHub |

## Instalación

```bash
git clone https://github.com/cristianl0pez-dev/lemoria.git
cd lemoria
chmod +x install.sh
./install.sh
opencode
```

El script `install.sh` levanta PostgreSQL en Docker, instala `lemoria` como comando global e inicializa la base de datos.

> **Detalles:** [INSTALL.md](INSTALL.md) — instalación paso a paso.

---

## Uso

`lemoria` se instala como comando global. Todos los comandos persisten en PostgreSQL automáticamente.

### Proyectos

```bash
lemoria project create "mi-api" -d "API REST de usuarios"
lemoria project list
lemoria project get <project-id>
```

### Conversaciones (memoria)

```bash
lemoria conv create <project-id> -t "Feature: login"
lemoria conv add <conv-id> user "necesito un endpoint POST /login"
lemoria conv add <conv-id> agent "implementado con JWT"
lemoria conv list <project-id>
```

### Flujo SDD

```bash
lemoria flow start <project-id> "sistema de autenticación JWT"
lemoria flow advance <prd-id>
lemoria flow complete <prd-id>
lemoria flow list <project-id>
```

### Tareas

```bash
lemoria task create <project-id> <prd-id> -t "modelo User" -d "tabla usuarios"
lemoria task list <project-id>
lemoria task status <task-id> in_progress
```

### Decisiones técnicas

```bash
lemoria decision log <project-id> -t "usar JWT" -d "se eligió JWT sobre sesiones" -r "stateless"
lemoria decision list <project-id>
```

### Agentes

```bash
lemoria agent register "mi-agente" "backend" -d "agente custom"
lemoria agent list
```

---

## OpenCode Integration

### Agentes disponibles

| Agente | Modo | Rol | Bash | Edit |
|--------|------|-----|------|------|
| `orchestrator` | **primary** (default) | Orquestador SDD | allow | deny |
| `backend-agent` | subagent | Implementación backend | allow | allow |
| `db-agent` | subagent | Base de datos y migraciones | allow | allow |
| `testing-agent` | subagent | Tests y calidad | allow | allow |
| `github-agent` | subagent | Trazabilidad GitHub | allow | deny |
| `review-agent` | subagent | Revisión técnica | deny | deny |
| `documentation-agent` | subagent | Documentación y Obsidian | allow | allow |

### Comandos rápidos (`@` en OpenCode)

| Comando | Descripción |
|---------|------------|
| `@new-feature` | Flujo SDD completo desde una idea |
| `@lemoria-project` | Crear o listar proyectos |
| `@lemoria-flow` | Iniciar flujo SDD |
| `@lemoria-agent` | Gestionar agentes |

### Flujo automático (orchestrator)

Cuando escribes **"quiero una función X"** en OpenCode, el orquestador ejecuta:

```
1. lemoria project list        → detecta o crea proyecto
2. lemoria conv create         → inicia conversación
3. lemoria conv add user       → registra tu pedido
4. lemoria flow start          → crea PRD
5. lemoria task create         → desglosa en tareas
6. @backend-agent              → implementa
7. @testing-agent              → escribe tests
8. @review-agent               → revisa
9. lemoria decision log        → registra decisiones
10. lemoria conv add agent     → consolida resultados
```

---

## SDD Flow (Spec Driven Development)

```
Idea → Spec → PRD → Tasks → Architecture → Implementation → Testing → Review → Commit → Push → Documentation → Memory Update
```

Cada ciclo completo queda registrado en PostgreSQL con trazabilidad total.

---

## Modelo de Datos

| Tabla | Descripción |
|-------|------------|
| `projects` | Proyectos de desarrollo |
| `conversations` | Sesiones de conversación |
| `messages` | Mensajes por conversación |
| `contexts` | Contexto jerárquico (global → project → task → agent) |
| `prds` | Product Requirements Documents |
| `specs` | Especificaciones técnicas |
| `tasks` | Tareas derivadas de PRDs |
| `decisions` | Decisiones técnicas registradas |
| `commits` | Commits vinculados a tareas |
| `pushes` | Pushes con PRs asociados |
| `files` | Archivos modificados por commit |
| `agents` | Agentes registrados en el sistema |
| `agent_executions` | Ejecuciones de agentes |
| `errors` | Errores registrados |
| `solutions` | Soluciones asociadas a errores |

---

## Estructura del proyecto

```
lemoria/
├── .opencode/
│   ├── agents/              # 7 agentes OpenCode (auto-descubiertos)
│   └── skills/lemoria/      # Skill de Lemoria
├── database/models/         # 15 modelos SQLAlchemy
├── docs/                    # PRD, ARCHITECTURE, ROADMAP, SDD
├── lemoria/                 # Código fuente Python
│   ├── cli.py               # CLI (Click)
│   ├── core.py              # Punto de entrada
│   ├── config.py            # Configuración (Pydantic)
│   ├── database.py          # Engine + Session
│   ├── project.py           # Servicio de proyectos
│   ├── memory.py            # Servicio de memoria
│   ├── orchestrator.py      # Orquestador de agentes
│   ├── flow.py              # Motor SDD
│   ├── vault.py             # Sincronización Obsidian
│   └── git_service.py       # Trazabilidad GitHub
├── vault/obsidian/          # Vault para Obsidian
├── opencode.jsonc           # Configuración OpenCode
├── docker-compose.yml       # PostgreSQL 16
├── Dockerfile               # Imagen Python
├── INSTALL.md               # Guía de instalación
└── install.sh               # Script de instalación
```

---

## Documentación

| Documento | Descripción |
|-----------|------------|
| [PRD](docs/PRD.md) | Product Requirements Document |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Arquitectura del sistema |
| [ROADMAP](docs/ROADMAP.md) | Roadmap del proyecto |
| [SDD](docs/SDD.md) | Spec Driven Development |
| [INSTALL.md](INSTALL.md) | Instalación detallada |

---

## Licencia

MIT
