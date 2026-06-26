<p align="center">
  <h1 align="center">🧠 Lemoria</h1>
  <p align="center">
    <strong>Sistema Operativo de Memoria y Orquestación para Desarrollo con IA</strong>
  </p>
  <p align="center">
    <em>Tu memoria persistente para el desarrollo asistido por inteligencia artificial.</em>
  </p>
  <p align="center">
    <a href="https://img.shields.io/badge/python-3.11%2B-blue" target="_blank"><img src="https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square&logo=python" alt="Python 3.11+" /></a>
    <a href="https://img.shields.io/github/license/devcristianlopez/lemoria" target="_blank"><img src="https://img.shields.io/github/license/devcristianlopez/lemoria?style=flat-square" alt="MIT License" /></a>
    <a href="https://img.shields.io/github/last-commit/devcristianlopez/lemoria" target="_blank"><img src="https://img.shields.io/github/last-commit/devcristianlopez/lemoria?style=flat-square" alt="Last Commit" /></a>
    <a href="https://img.shields.io/github/repo-size/devcristianlopez/lemoria" target="_blank"><img src="https://img.shields.io/github/repo-size/devcristianlopez/lemoria?style=flat-square" alt="Repo Size" /></a>
    <a href="https://img.shields.io/github/actions/workflow/status/devcristianlopez/lemoria/ci.yml?style=flat-square&logo=githubactions" target="_blank"><img src="https://img.shields.io/github/actions/workflow/status/devcristianlopez/lemoria/ci.yml?style=flat-square&logo=githubactions" alt="CI" /></a>
    <a href="https://img.shields.io/badge/tests-41-brightgreen?style=flat-square&label=tests" target="_blank"><img src="https://img.shields.io/badge/tests-41-brightgreen?style=flat-square&label=tests" alt="Tests" /></a>
  </p>
</p>

---

**Lemoria** es una herramienta CLI en Python que convierte tu flujo de desarrollo en un proceso trazable, orquestado por agentes de IA. Cada idea, cada decisión, cada línea de código queda registrada en PostgreSQL con trazabilidad completa, desde la especificación inicial hasta el push y la documentación.

Instálalo **una sola vez** y todos tus proyectos —limpios, separados, sin configurar nada— heredan los agentes, la base de datos y la memoria persistente.

---

## ✨ Features

- 🎯 **SDD Flow completo** — 15 pasos: discovery → idea → spec → PRD → tasks → architecture → implementation → testing → review → commit → push → documentation → memory update
- 🤖 **8 agentes OpenCode** — Un orquestador que delega automáticamente a agentes especializados (implementation, frontend, DB, testing, GitHub, review, documentation)
- 🗃️ **Trazabilidad total** — Cada proyecto, PRD, tarea, decisión y flow step se persiste en PostgreSQL con relaciones y metadatos
- 🐳 **PostgreSQL en Docker** — Base de datos aislada, reproducible, lista en segundos
- 🔌 **CLI global** — `lemoria` disponible en cualquier terminal tras la instalación
- 📂 **Proyectos independientes** — Cada proyecto vive en su propia carpeta, sin contaminación cruzada
- 📚 **Obsidian vault** — Sincronización bidireccional opcional: exporta a markdown y restaura la DB desde el vault
- 📋 **Decisiones registradas** — Cada cambio importante queda documentado como ADR antes de implementar
- 🔄 **State machine** — Cada paso del flujo se registra en `flow_steps`, permitiendo retomar sesiones tras pérdida de contexto
- 🧪 **41 tests automatizados** — pytest con SQLite in-memory, CI en GitHub Actions (Python 3.11/3.12/3.13)
- 🏷️ **8 enums tipados** — Todos los status con `CheckConstraint` en DB para integridad a nivel de base de datos
- 📡 **Context7 MCP** — Documentación en tiempo real de librerías y frameworks vía MCP server

---

## 🚀 Quick Start

```bash
# 1. Clona el repositorio
git clone https://github.com/devcristianlopez/lemoria.git && cd lemoria

# 2. Ejecuta el instalador (elige modo GLOBAL para usar agentes en cualquier proyecto)
./install.sh

# 3. ¡Listo! Crea tu primer proyecto desde cualquier carpeta
mkdir ~/mi-api && cd ~/mi-api
opencode
# → "Quiero un endpoint POST /login con JWT"
# → El orquestador crea el proyecto, delega y registra todo
```

> **Nota:** Después de instalar, el repositorio `lemoria/` es prescindible. Los agentes quedan en `~/.config/opencode/agents/` y el comando `lemoria` está disponible globalmente.

Comandos esenciales:

```bash
lemoria project list               # Lista todos tus proyectos
lemoria flow list <project-id>     # PRDs del proyecto
lemoria flow status <flow-id>      # Estado del state machine (pasos completados/faltantes)
lemoria flow step <flow-id> <step> # Registrar paso del flujo
lemoria task list <project-id>     # Tareas del proyecto
lemoria decision list <project-id> # Decisiones registradas
lemoria spec list <project-id>     # Especificaciones técnicas
lemoria error list <project-id>    # Errores registrados
lemoria vault sync <project-id>    # Sincronizar DB → Obsidian vault
lemoria vault restore <project-id> # Restaurar DB desde vault
lemoria context set/get <project>  # Contexto jerárquico
lemoria --help                     # Ayuda completa
```

---

## 📋 SDD Flow — Spec Driven Development

Lemoria implementa el flujo **SDD** en 12 pasos, donde cada etapa produce un artefacto que alimenta la siguiente:

```
💡 User Request
   │
   ↓
🔍 Discovery        → Preguntas esenciales (tech stack, DB, auth, deploy, etc.)
   │
   ↓
📐 Spec              → Especificación detallada
   │
   ↓
📄 PRD               → Product Requirements Document
   │
   ↓
📋 Tasks             → Desglose en tareas atómicas (INVEST)
   │
   ↓
🏗️ Architecture      → Diseño arquitectónico
   │
   ↓
⚙️ Implementation    → Codificación
   │
   ↓
🧪 Testing           → Pruebas automatizadas
   │
   ↓
👀 Review            → Revisión técnica
   │
   ↓
💾 Commit            → Registro con trazabilidad (ref. a tarea)
   │
   ↓
📤 Push              → Publicación al remoto
   │
   ↓
📖 Documentation     → Actualización de docs y notas
   │
   ↓
🧠 Memory Update     → Persistencia en memoria del agente
```

### State Machine

Cada ejecución del flujo SDD se registra como un **flow** en la tabla `flow_steps`. El orquestador consulta el estado actual al iniciar, permitiendo **reanudar flujos interrumpidos** sin pérdida de contexto:

```
flow step <flow-id> <step> --status completed|running|failed
flow status <flow-id>        # Muestra todos los pasos + overall state
```

Cada paso tiene: `id`, `flow_id`, `step`, `status`, `started_at`, `completed_at`, `output`.

### Principios SDD

| # | Principio |
|---|-----------|
| 1 | Toda implementación comienza con un **PRD** |
| 2 | Toda tarea se deriva de un **PRD o spec** |
| 3 | Todo commit referencia una **tarea** |
| 4 | Toda decisión se registra **antes** de implementar |
| 5 | La documentación se actualiza en **cada ciclo** |
| 6 | Todo paso del flujo se persiste como **flow step** en la DB |

---

## 🤖 Agentes OpenCode

Lemoria incluye **8 agentes** en inglés, sin dependencia de lenguaje/framework. El `orchestrator` es el agente por defecto; los demás son subagentes a los que delega según la fase del flujo SDD.

| Agente | Modo | Rol |
|--------|------|-----|
| 🧠 **Orchestrator** | `primary` (default) | Decide el flujo SDD, delega tareas, ejecuta closing checklist |
| ⚙️ **Implementation Agent** | `subagent` | Implementación de código (backend, scripts, lógica) |
| 🎨 **Frontend Agent** | `subagent` | Implementación de UI/UX (componentes, estilos, routing) |
| 🗄️ **DB Agent** | `subagent` | Gestión de esquemas y modelos de base de datos |
| 🧪 **Testing Agent** | `subagent` | Escritura y ejecución de tests |
| 👁️ **Review Agent** | `subagent` | Revisión técnica de código y PRDs |
| 🐙 **GitHub Agent** | `subagent` | Trazabilidad GitHub: commits, PRs, issues |
| 📝 **Documentation Agent** | `subagent` | Documentación técnica y sincronización con vault |

Los agentes y skills se copian tanto a nivel proyecto (`.opencode/`) como global (`~/.config/opencode/`), y están disponibles en cualquier proyecto sin configuración adicional.

### Configuración: `opencode.json` vs `opencode.jsonc`

Lemoria usa dos archivos de configuración de OpenCode, cada uno con un propósito distinto:

| Archivo | Ubicación | Función | Comentarios |
|---------|-----------|---------|-------------|
| `opencode.jsonc` | `~/Projects/lemoria/` (en el repo) | Configuración del proyecto Lemoria: agente default, skills paths, comandos personalizados | ✅ Soporta `//` y `/* */` |
| `opencode.json` | `~/.config/opencode/` (global) | Configuración global del usuario: **personalidad de la AI**, idioma de interacción, MCP servers | ❌ JSON puro, sin comentarios |

**¿Cuál es la diferencia?**

- **`opencode.jsonc`** está en el repo y define cosas del proyecto Lemoria (qué agente se carga por defecto, dónde buscar skills). Usa la extensión `.jsonc` porque así podemos dejar comentarios en el archivo sin que OpenCode proteste.

- **`opencode.json`** lo configura cada usuario en su home y es donde se define **el idioma y tono de la AI**. Si quieres que la AI te hable en español, inglés, o en cualquier otro estilo, es ahí donde se configura.

**¿Por qué importa?**

Los agentes y skills de Lemoria están todos en **inglés** (son universales), pero la AI se comunica contigo en el idioma que definas en tu `~/.config/opencode/opencode.json`. Por ejemplo:

```json
// ~/.config/opencode/opencode.json
{
  "agent": {
    "plan": {
      "prompt": "Háblame en español chileno relajado pero correcto. Trátame de 'tú'."
    }
  }
}
```

Esto significa que **los agentes trabajan en inglés** (código, commits, docs), pero **tú interactúas en el idioma que prefieras**.

---

## 🗂️ Project Structure

```
lemoria/
├── lemoria/                  # CLI principal (Click)
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                # Punto de entrada CLI (14+ comandos)
│   ├── config.py             # Configuración vía pydantic-settings
│   ├── core.py               # Orquestador principal (Lemoria class)
│   ├── database.py           # Conexión y sesión SQLAlchemy
│   ├── flow.py               # Motor SDD + state machine (FlowEngine)
│   ├── git_service.py        # Servicio de commits/pushes
│   ├── memory.py             # Servicio de memoria (conversaciones)
│   ├── orchestrator.py       # Registro y delegación de agentes
│   ├── project.py            # CRUD de proyectos
│   └── vault.py              # Integración Obsidian bidireccional
├── database/                 # Capa de base de datos
│   ├── enums.py              # 8 enums tipados (PRDStatus, TaskStatus, etc.)
│   ├── models/               # 16 modelos SQLAlchemy
│   │   ├── agent.py
│   │   ├── commit.py
│   │   ├── conversation.py
│   │   ├── decision.py
│   │   ├── flow_step.py      # State machine: pasos del flujo SDD
│   │   ├── prd.py
│   │   ├── project.py
│   │   ├── task.py
│   │   └── ... (8 más)
│   └── seed/                 # Datos semilla
├── docs/                     # Documentación
│   ├── ARCHITECTURE.md
│   ├── PRD.md
│   ├── ROADMAP.md
│   └── SDD.md
├── vault/                    # Obsidian vault (bidireccional)
├── .opencode/
│   ├── agents/               # Definiciones de los 8 agentes
│   └── skills/               # 7 skills Lemoria (frontend, backend, database, etc.)
├── tests/                    # 41 tests (pytest, SQLite in-memory)
│   ├── conftest.py
│   ├── test_cli.py           # 10 tests
│   ├── test_flow.py          # 13 tests
│   ├── test_project.py       # 6 tests
│   └── test_vault.py         # 9 tests
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions: matrix 3.11/3.12/3.13, PostgreSQL, ruff, Codecov
├── docker-compose.yml        # PostgreSQL 16
├── install.sh                # Instalación automatizada (con Context7 opcional)
├── pyproject.toml            # Configuración del proyecto + pytest
├── opencode.jsonc            # Configuración de OpenCode
├── INSTALL.md                # Guía de instalación detallada
├── LICENSE                   # MIT License
└── README.md                 # Este archivo
```

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| **Lenguaje** | [Python 3.11+](https://www.python.org/) |
| **CLI** | [Click](https://click.palletsprojects.com/) |
| **ORM** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) |
| **Base de Datos** | [PostgreSQL 16](https://www.postgresql.org/) (Docker) |
| **Migraciones** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Validación** | [Pydantic 2.0](https://docs.pydantic.dev/) |
| **HTTP Client** | [HTTPX](https://www.python-httpx.org/) |
| **Git** | [GitPython](https://gitpython.readthedocs.io/) |
| **Terminal UI** | [Rich](https://rich.readthedocs.io/) |
| **Agentes** | [OpenCode](https://opencode.ai) (8 agentes) |
| **Skills** | 7 skills modulares (frontend, backend, database, testing, code-review, git-workflow, documentation) |
| **Documentación en tiempo real** | [Context7 MCP](https://context7.com) |
| **Vault** | [Obsidian](https://obsidian.md/) (bidireccional) |
| **Testing** | [pytest](https://pytest.org/) — 41 tests |
| **Linting** | [Ruff](https://docs.astral.sh/ruff/) |
| **CI/CD** | [GitHub Actions](https://github.com/features/actions) (matrix 3.11/3.12/3.13) |

---

## 📚 Documentación

| Recurso | Descripción |
|---------|-------------|
| [📖 INSTALL.md](INSTALL.md) | Instalación detallada paso a paso |
| [📄 PRD](docs/PRD.md) | Product Requirements Document |
| [🏗️ ARCHITECTURE](docs/ARCHITECTURE.md) | Arquitectura del sistema |
| [🗺️ ROADMAP](docs/ROADMAP.md) | Roadmap del proyecto |
| [📋 SDD](docs/SDD.md) | Spec Driven Development — flujo completo |
| [🏷️ Enums](database/enums.py) | 8 enums tipados con CheckConstraints |

---

## 📦 Instalación Detallada

La instalación tarda **menos de 2 minutos** y es completamente automatizada:

1. **Verifica requisitos** — Python 3.11+, Docker y Docker Compose
2. **Inicia PostgreSQL** — Se levanta automáticamente con `docker compose up -d`
3. **Instala el CLI** — `pip install -e .` registra el comando `lemoria`
4. **Configura agentes** — Elige modo **Global** (disponible en cualquier proyecto) o **Proyecto** (local)
5. **Inicializa la DB** — `lemoria init` crea las tablas y el vault

Para más detalles, consulta [INSTALL.md](INSTALL.md).

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Este proyecto sigue el flujo SDD para todas las funcionalidades:

1. Abre un **issue** describiendo la idea o el bug
2. El flujo SDD guiará la especificación, implementación y documentación
3. Cada PR debe incluir trazabilidad a la tarea correspondiente

---

## 📄 Licencia

**MIT License** — Copyright © 2026 [Cristian López](https://github.com/devcristianlopez)

Se concede permiso, sin cargo, a cualquier persona que obtenga una copia de este software y de los archivos de documentación asociados, para utilizarlo sin restricción, incluyendo sin limitación los derechos de usar, copiar, modificar, fusionar, publicar, distribuir, sublicenciar y/o vender copias del Software.

---

<p align="center">
  <sub>Hecho con ❤️ por <a href="https://github.com/devcristianlopez">@devcristianlopez</a></sub>
  <br>
  <sub>✨ Lemoria — Nunca olvides por qué escribes cada línea de código ✨</sub>
</p>
