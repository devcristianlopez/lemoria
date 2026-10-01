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
    <a href="https://img.shields.io/badge/tests-228-brightgreen?style=flat-square&label=tests" target="_blank"><img src="https://img.shields.io/badge/tests-228-brightgreen?style=flat-square&label=tests" alt="Tests" /></a>
  </p>
</p>

---

**Lemoria** es una herramienta CLI en Python que convierte tu flujo de desarrollo en un proceso trazable, orquestado por agentes de IA. Cada idea, cada decisión, cada línea de código queda registrada en PostgreSQL con trazabilidad completa, desde la especificación inicial hasta el push y la documentación.

Instálalo **una sola vez** y todos tus proyectos —limpios, separados, sin configurar nada— heredan los agentes, la base de datos y la memoria persistente.

---

## ✨ Features

- 🎯 **SDD Flow completo** — 15 pasos: discovery → idea → spec → PRD → tasks → architecture → implementation → testing → review → commit → push → documentation → memory update
- 🤖 **8 agentes OpenCode** — Un orquestador que delega automáticamente a agentes especializados (implementation, frontend, DB, testing, GitHub, review, documentation)
- 🧭 **Gestión de agentes** — Los subagentes viven en la DB, y su modelo se ve y se cambia por agente (`lemoria agent sync|model|status`)
- 📊 **Telemetría de opencode** — Sesiones, tokens y costo por agente, con widget propio de Omarchy aislado de Codex/Claude/Fireworks
- 🗃️ **Trazabilidad total** — Cada proyecto, PRD, tarea, decisión y flow step se persiste en PostgreSQL con relaciones y metadatos
- 🐘 **PostgreSQL nativo o en Docker** — Usa el servidor que ya tengas andando; Docker es la alternativa, no el requisito
- 🔌 **CLI global** — `lemoria` disponible en cualquier terminal tras la instalación
- 📂 **Proyectos independientes** — Cada proyecto vive en su propia carpeta, sin contaminación cruzada
- 📚 **Obsidian vault** — Sincronización bidireccional opcional: exporta a markdown y restaura la DB desde el vault (memoria privada, guardada fuera de repos git).
- 📋 **Decisiones registradas** — Cada cambio importante queda documentado como ADR antes de implementar
- 🔄 **State machine** — Cada paso del flujo se registra en `flow_steps`, permitiendo retomar sesiones tras pérdida de contexto
- 🧪 **228 tests automatizados** — pytest con SQLite in-memory, CI en GitHub Actions (Python 3.11/3.12/3.13)
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

**Requisitos:** Python >= 3.11, [uv](https://docs.astral.sh/uv/) y PostgreSQL >= 14
(nativo del sistema o Docker — da igual cuál). Docker no es obligatorio y `pip`
tampoco: el instalador usa `uv` primero, y por eso funciona en Arch con
Python 3.14 sin pelear con PEP 668. Si venís de otra distro y querés el detalle,
[`INSTALL.md`](INSTALL.md) explica por qué `pip install` falla ahí y cómo
desbloquearlo sin romper el sistema.

Comandos esenciales:

```bash
lemoria project list               # Lista todos tus proyectos
lemoria flow list <project-id>     # PRDs del proyecto
lemoria flow status <flow-id>      # Estado del state machine (pasos completados/faltantes)
lemoria flow step <flow-id> <step> # Registrar paso del flujo
lemoria task list <project-id>     # Tareas del proyecto
lemoria commit sync                # Importa git log y enlaza commits por trailer Task: <uuid>
lemoria commit list --project <id> # Commits registrados y su tarea enlazada
lemoria commit add <sha> --task <task-id>  # Registrar un commit puntual
lemoria decision list <project-id> # Decisiones registradas
lemoria spec list <project-id>     # Especificaciones técnicas
lemoria error list <project-id>    # Errores registrados
lemoria vault sync <project-id>    # Sincronizar DB → Obsidian vault
lemoria vault restore <project-id> # Restaurar DB desde vault
lemoria context set/get <project>  # Contexto jerárquico
lemoria --help                     # Ayuda completa
```

Los commits se enlazan a tareas por convención de mensaje:

```text
Task: <task-id>
```

`lemoria commit sync` reconstruye la trazabilidad histórica leyendo ese trailer
con GitPython; `lemoria commit add <sha> --task <id>` sirve cuando necesitas
registrar un SHA puntual. El vault exporta esos enlaces en `commits.md`, así que
puedes navegar PRD → Task → Commit desde Obsidian.

### 🔒 El vault nunca se sube a git

El vault contiene **memoria privada**: conversaciones, ADRs, PRDs y commits de
todos tus proyectos. Por eso vive fuera de cualquier repositorio:

```
~/.lemoria/vault/          ← por defecto (fuera de todo repo)
```

Si alguien configura `LEMORIA_VAULT_PATH` dentro de un repositorio, Lemoria se
autoprotege: `VaultService.protect_from_git()` detecta el `.git` más cercano y
**agrega el vault al `.gitignore`** de ese repo antes de escribir, de forma
idempotente. Nunca falla: si el `.gitignore` no se puede escribir, avisa por
stderr y sigue operando.

```console
$ lemoria vault sync <project-id>
  ! Vault is inside a git repo — added 'vault/obsidian/' to /ruta/al/repo/.gitignore
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

Los agentes, skills y comandos se copian tanto a nivel proyecto (`.opencode/`) como global (`~/.config/opencode/`), y están disponibles en cualquier proyecto sin configuración adicional. En OpenCode v2 los comandos se invocan como slash commands, por ejemplo:

```text
/lemoria quiero implementar autenticación con JWT
```

Nota: en configuración JSON/JSONC de OpenCode v2 la clave correcta es `commands` en plural. La clave/directorio singular `command` es legacy y no se usa para nuevas instalaciones.

### Menú Ctrl+P de Lemoria

Además del slash command, el instalador deja un plugin del TUI que agrega un grupo **Lemoria** a la paleta de comandos de **Ctrl+P**: estado de los agentes, fijar o limpiar modelo y esfuerzo, `sync` y desinstalación. Todo se elige con diálogos de selección —no hay que escribir nada— y solo se ofrecen los modelos que OpenCode habilita para tu cuenta. Los detalles están en [INSTALL.md](INSTALL.md#menú-ctrlp-de-lemoria).

### Configuración: `opencode.json` vs `opencode.jsonc`

Lemoria usa dos archivos de configuración de OpenCode, cada uno con un propósito distinto:

| Archivo | Ubicación | Función | Comentarios |
|---------|-----------|---------|-------------|
| `opencode.jsonc` | `~/Projects/lemoria/` (en el repo) | Configuración del proyecto Lemoria: agente default, skills y comandos personalizados | ✅ Soporta `//` y `/* */` |
| `opencode.json` | `~/.config/opencode/` (global) | Configuración global del usuario: **personalidad de la AI**, idioma de interacción, MCP servers | ❌ JSON puro, sin comentarios |

**¿Cuál es la diferencia?**

- **`opencode.jsonc`** está en el repo y define cosas del proyecto Lemoria (qué agente se carga por defecto, dónde buscar skills). Usa la extensión `.jsonc` porque así podemos dejar comentarios en el archivo sin que OpenCode proteste.

- **`opencode.json`** lo configura cada usuario en su home y es donde se define **el idioma y tono de la AI**. Si quieres que la AI te hable en español, inglés, o en cualquier otro estilo, es ahí donde se configura.

**¿Por qué importa?**

Los agentes y skills de Lemoria están todos en **inglés** (son universales), pero la AI se comunica contigo en el idioma que definas en tu `~/.config/opencode/opencode.json`. Por ejemplo:

```json
// ~/.config/opencode/opencode.json
{
  "agents": {
    "plan": {
      "system": "Háblame en español chileno relajado pero correcto. Trátame de 'tú'."
    }
  }
}
```

Esto significa que **los agentes trabajan en inglés** (código, commits, docs), pero **tú interactúas en el idioma que prefieras**.

---

## 🧭 Gestión de agentes y telemetría

Lemoria no solo delega: también **registra** a sus subagentes, te deja **cambiar el modelo de cada uno** y publica el **consumo** en su widget propio de Omarchy.

### El concepto clave: el modelo se hereda

OpenCode lee la clave `model` del frontmatter de cada agente. **Si un agente no la declara, hereda el modelo de quien lo invoca.**

Los 7 subagentes de Lemoria no declaran modelo, así que los 7 usan el modelo del orquestador. Por eso la columna `agents.model` está vacía:

> **No es un bug.** Es el comportamiento de OpenCode. Fijar un modelo es **opcional y por agente**, y una columna vacía significa exactamente eso: *"este agente no fija modelo"*.

Fijarlo es una línea en su frontmatter, y se hace con un comando:

```bash
lemoria agent model review-agent anthropic/claude-sonnet-4-5   # fija modelo
lemoria agent model review-agent anthropic/claude-sonnet-4-5 --variant high
lemoria agent model review-agent          # sin argumentos: muestra el actual
```

El comando **edita el `.md`**, no la DB. El markdown es la fuente de verdad y la base solo lo refleja. `lemoria agent status` distingue las tres situaciones:

| `source` | Significado |
|---|---|
| `inherits` | sin `model` en el frontmatter → usa el modelo de quien lo invoca |
| `pinned` | con `model` en el frontmatter → ese modelo, siempre |
| `builtin` | agente propio de OpenCode (`build`, `plan`, …) sin `.md` que configurar |

### Comandos

| Comando | Qué hace |
|---|---|
| `lemoria agent sync [--dry-run] [--dir PATH]` | Refleja `.opencode/agents/*.md` en la tabla `agents` |
| `lemoria agent list` | Agentes registrados |
| `lemoria agent status [--json]` | Modelo efectivo, sesiones, sesiones vivas y tokens **por agente** |
| `lemoria agent model <name> [model] [--variant V]` | Fija o muestra el modelo de un agente |

`--dry-run` informa qué cambiaría sin escribir nada. La ruta de los `.md` sale de `LEMORIA_OPENCODE_AGENTS_DIR` (default `./.opencode/agents`).

### Ver quién está corriendo y cuánto consumió

`lemoria agent status` es el desglose por subagente que el panel **no** tiene:

```console
$ lemoria agent status
agent                  source   model            variant   sess  live    tokens
-------------------------------------------------------------------------------
orchestrator           inherits big-pickle       default      6    1*    137.2M
implementation-agent   inherits big-pickle       default     36     0     35.7M
testing-agent          inherits big-pickle       default      6     0      7.7M
review-agent           inherits big-pickle       default      9     0      2.2M
-------------------------------------------------------------------------------
build                  builtin  big-pickle       default      5     0     46.2M
plan                   builtin  big-pickle       default      2     0      1.6M

inherits = no model in frontmatter, so opencode uses the calling agent's
builtin   = opencode's own agent, no .md to pin a model on
*         = session updated in the last 5 minutes
```

`live` con `*` marca una sesión tocada en los últimos 5 minutos: opencode no expone un flag "corriendo", así que la recencia es la señal honesta. Con `--json` debería salir lo mismo estructurado más el `cost` real por agente.

El `--json` incluye además los agentes propios de opencode (`build`, `plan`, …) marcados con `managed: false`, para que puedas distinguirlos de los que Lemoria administra.

### El panel de Omarchy

Omarchy ya trae un panel de agentes para Claude/Codex/Fireworks. Lemoria **no escribe en ese directorio**: instala un plugin propio, `lemoria.usage`, y lee un record privado en `~/.local/state/lemoria/omarchy/usage.json` para no tocar el panel nativo.

```bash
lemoria omarchy install --interval 1min  # plugin + record privado + timer de usuario, lo activa
lemoria budget 500M              # opcional: presupuesto mensual en tokens
lemoria omarchy record --print   # inspeccionar el JSON sin escribir
lemoria omarchy where            # dónde busca Omarchy los records
```

`install` también intenta ejecutar `omarchy plugin enable lemoria.usage --after omarchy.agents`.
Si Omarchy no está en `PATH` o el enable automático falla, corré ese comando manualmente y recargá la shell/barra de Omarchy.
El plugin siempre queda bajo control de Lemoria: usa `~/.config/omarchy/plugins/lemoria.usage` y el record privado `~/.local/state/lemoria/omarchy/usage.json`, no el directorio nativo de `omarchy.agents`.

El widget propio deja el **total acumulado** siempre visible en la barra. Al abrirlo muestra:

- total histórico, sesiones, prompts y rango de fechas;
- tokens de hoy y últimos 7 días;
- tabla con **todos los agentes conocidos**, aunque no tengan uso, total consolidado, tokens de hoy, sesiones, prompts y el modelo de display actual/configurado/default; si el modelo observado por telemetría histórica difiere, lo muestra aparte como `obs ...`;
- presupuesto mensual en tokens solo si lo configurás.

El record del plugin es privado (`~/.local/state/lemoria/omarchy/usage.json`): `omarchy.agents` no lo ve, así que Claude/Codex/Fireworks quedan intactos. El timer también sanea el `codex.json` nativo cuando el collector de Codex devuelve el error intermitente `account/read`.

### Timer de actualización

`lemoria omarchy install` escribe el plugin, publica un record una vez y deja un timer de **usuario** (systemd `--user`) que refresca cada minuto:

```bash
lemoria omarchy install --interval 1min  # cada 1 min, y lo activa
lemoria omarchy install --interval 30min # otra frecuencia
lemoria omarchy install --no-enable      # solo escribe plugin, record y units
```

Si el panel no aparece, verificá en este orden:

```bash
omarchy plugin enable lemoria.usage --after omarchy.agents
test -f ~/.config/omarchy/plugins/lemoria.usage/Panel.qml
test -f ~/.local/state/lemoria/omarchy/usage.json || lemoria omarchy record
systemctl --user status lemoria-usage.timer
systemctl --user list-timers lemoria-usage.timer --no-pager
```

Con cero uso registrado el botón ya no colapsa: muestra `0` y al abrirlo enseña el estado vacío o el motivo (`opencode data unavailable`, etc.).
Si no ves ni el `0`, el problema está en la activación del plugin o en la recarga de Omarchy, no en el record de uso.
Después de actualizar el plugin, los cambios visuales de layout/márgenes pueden requerir `omarchy restart shell`; `rescanPlugins` no siempre refresca la instancia visible.

Es reversible:

```bash
lemoria omarchy uninstall
```

Las units viven en `~/.config/systemd/user/lemoria-usage.{service,timer}`; el plugin vive en `~/.config/omarchy/plugins/lemoria.usage`.

### Configuración

| Variable | Default | Para qué |
|---|---|---|
| `LEMORIA_OPENCODE_AGENTS_DIR` | `./.opencode/agents` | De dónde lee los `.md` de agentes |

La tabla `agents` ganó las columnas `model` y `variant`. La migración es idempotente y se aplica sola en `lemoria init`.

> Detalle completo, contrato del record y cómo quitar un pin: [📄 AGENT-MANAGEMENT](docs/AGENT-MANAGEMENT.md)

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
│   ├── database.py           # Conexión, sesión y migración idempotente
│   ├── agents.py             # Sync .opencode/agents/*.md → tabla agents
│   ├── opencode_telemetry.py # Lectura de solo lectura del opencode.db
│   ├── omarchy.py            # Record privado + plugin lemoria.usage para Omarchy
│   ├── flow.py               # Motor SDD + state machine (FlowEngine)
│   ├── git_history.py        # Lectura de metadatos desde git (GitPython)
│   ├── git_service.py        # Servicio de commits/pushes y trazabilidad task→commit
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
├── .opencode/
│   ├── agents/               # Definiciones de los 8 agentes
│   ├── commands/             # Slash commands de OpenCode, como /lemoria
│   └── skills/               # 7 skills Lemoria (frontend, backend, database, etc.)
├── tests/                    # 228 tests (pytest, SQLite in-memory)
│   ├── conftest.py
│   ├── test_agents.py        # 88 tests — modelos, pin/unpin, telemetría por agente
│   ├── test_installer.py     # 71 tests — decisiones de installer/lib.sh en un PATH falso
│   ├── test_vault.py         # 20 tests
│   ├── test_cli.py           # 17 tests
│   ├── test_flow.py          # 17 tests
│   ├── test_project.py       # 7 tests
│   └── test_budget.py        # 8 tests
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions: matrix 3.11/3.12/3.13, PostgreSQL, ruff, Codecov
├── docker-compose.yml        # PostgreSQL 16 (alternativa al servidor nativo)
├── install.sh                # Instalación automatizada (con Context7 opcional)
├── installer/
│   └── lib.sh                # Decisiones del instalador, separadas para testearlas
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
| **Base de Datos** | [PostgreSQL >= 14](https://www.postgresql.org/) (nativo o Docker; el compose del repo usa 16) |
| **Migraciones** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Validación** | [Pydantic 2.0](https://docs.pydantic.dev/) |
| **HTTP Client** | [HTTPX](https://www.python-httpx.org/) |
| **Git** | [GitPython](https://gitpython.readthedocs.io/) |
| **Terminal UI** | [Rich](https://rich.readthedocs.io/) |
| **Agentes** | [OpenCode](https://opencode.ai) (8 agentes) |
| **Skills** | 7 skills modulares (frontend, backend, database, testing, code-review, git-workflow, documentation) |
| **Documentación en tiempo real** | [Context7 MCP](https://context7.com) |
| **Vault** | [Obsidian](https://obsidian.md/) (bidireccional) |
| **Testing** | [pytest](https://pytest.org/) — 228 tests |
| **Linting** | [Ruff](https://docs.astral.sh/ruff/) |
| **CI/CD** | [GitHub Actions](https://github.com/features/actions) (matrix 3.11/3.12/3.13) |

---

## 📚 Documentación

| Recurso | Descripción |
|---------|-------------|
| [📖 INSTALL.md](INSTALL.md) | Instalación detallada paso a paso |
| [📄 PRD](docs/PRD.md) | Product Requirements Document |
| [🏗️ ARCHITECTURE](docs/ARCHITECTURE.md) | Arquitectura del sistema |
| [🧭 AGENT-MANAGEMENT](docs/AGENT-MANAGEMENT.md) | Gestión de subagentes, modelos y telemetría |
| [🗺️ ROADMAP](docs/ROADMAP.md) | Roadmap del proyecto |
| [📋 SDD](docs/SDD.md) | Spec Driven Development — flujo completo |
| [🏷️ Enums](database/enums.py) | 8 enums tipados con CheckConstraints |

---

## 📦 Instalación Detallada

La instalación tarda **menos de 2 minutos** y es completamente automatizada:

1. **Verifica requisitos** — Python 3.11+ y cómo llegás a PostgreSQL (nativo, Docker, o ninguno)
2. **Resuelve la base** — Si algo ya responde en `localhost:5432` lo respeta y no lo toca; si no, levanta Docker. Sin ninguna de las dos, se detiene y te guía
3. **Instala el CLI** — Prueba `uv` → venv propio → `pip`, en ese orden. El primero es el recomendado: aísla solo, sin `sudo` y sin tocar el intérprete del sistema
4. **Configura agentes** — Elige modo **Global** (disponible en cualquier proyecto) o **Proyecto** (local)
5. **Inicializa la DB** — `lemoria init` crea las tablas y el vault

Para más detalles —incluido por qué `pip install` falla en Arch con Python 3.14
y por qué el instalador **no** te pide sumarte al grupo `docker`— consulta
[INSTALL.md](INSTALL.md).

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
