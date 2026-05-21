# Lemoria

**Sistema Operativo de Memoria y Orquestación para Desarrollo con IA**

Lemoria se installa **una sola vez** y queda disponible globalmente. Tus proyectos de desarrollo van en carpetas separadas y limpias.

```
Lemoria (instalación global)
├── CLI: lemoria (comando global)
├── Agentes: ~/.config/opencode/agents/ (7 agentes)
├── PostgreSQL: Docker (siempre corriendo)
└── Obsidian vault: donde tú elijas

Tus proyectos (carpetas independientes)
├── /home/tu/mi-api/
├── /home/tu/web-app/
└── /home/tu/otro-proyecto/
     └── opencode .  ← agentes globales disponibles
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

## Instalación (una sola vez)

```bash
git clone https://github.com/cristianl0pez-dev/lemoria.git
cd lemoria
./install.sh          # → elegir modo GLOBAL
```

Esto instala `lemoria` como comando global, copia los 7 agentes a `~/.config/opencode/agents/` y levanta PostgreSQL.

> **El repo `lemoria/` ya no hace falta después de instalar.** Puedes borrarlo.

## Cómo trabajar

Creas una carpeta vacía para tu proyecto, abres OpenCode ahí, y los agentes globales están disponibles:

```bash
mkdir ~/mi-api && cd ~/mi-api
opencode
# → "quiero un endpoint POST /login con JWT"
# → El orquestador crea el proyecto en Lemoria, delega a agentes, registra todo
```

Todos los comandos `lemoria` persisten automáticamente en PostgreSQL:

```bash
lemoria project list              # todos tus proyectos
lemoria flow list <project-id>    # PRDs del proyecto
lemoria task list <project-id>    # tareas del proyecto
lemoria decision list <project-id> # decisiones registradas
```

## Agentes OpenCode

| Agente | Modo | Rol |
|--------|------|-----|
| `orchestrator` | **primary** (default) | Orquestador SDD |
| `backend-agent` | subagent | Implementación backend |
| `db-agent` | subagent | Base de datos |
| `testing-agent` | subagent | Tests |
| `github-agent` | subagent | Trazabilidad GitHub |
| `review-agent` | subagent | Revisión técnica |
| `documentation-agent` | subagent | Documentación |

## Documentación

- [INSTALL.md](INSTALL.md) — Instalación detallada
- [PRD](docs/PRD.md) — Product Requirements Document
- [ARCHITECTURE](docs/ARCHITECTURE.md) — Arquitectura
- [ROADMAP](docs/ROADMAP.md) — Roadmap
- [SDD](docs/SDD.md) — Spec Driven Development
