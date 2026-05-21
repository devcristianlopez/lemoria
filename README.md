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
    <a href="https://img.shields.io/github/license/cristianl0pez-dev/lemoria" target="_blank"><img src="https://img.shields.io/github/license/cristianl0pez-dev/lemoria?style=flat-square" alt="MIT License" /></a>
    <a href="https://img.shields.io/github/last-commit/cristianl0pez-dev/lemoria" target="_blank"><img src="https://img.shields.io/github/last-commit/cristianl0pez-dev/lemoria?style=flat-square" alt="Last Commit" /></a>
    <a href="https://img.shields.io/github/repo-size/cristianl0pez-dev/lemoria" target="_blank"><img src="https://img.shields.io/github/repo-size/cristianl0pez-dev/lemoria?style=flat-square" alt="Repo Size" /></a>
    <a href="https://img.shields.io/badge/made%20with-%E2%9D%A4%EF%B8%8F-red?style=flat-square" target="_blank"><img src="https://img.shields.io/badge/made%20with-%E2%9D%A4%EF%B8%8F-red?style=flat-square" alt="Made with love" /></a>
  </p>
</p>

---

**Lemoria** es una herramienta CLI en Python que convierte tu flujo de desarrollo en un proceso trazable, orquestado por agentes de IA. Cada idea, cada decisión, cada línea de código queda registrada en PostgreSQL con trazabilidad completa, desde la especificación inicial hasta el push y la documentación.

Instálalo **una sola vez** y todos tus proyectos —limpios, separados, sin configurar nada— heredan los agentes, la base de datos y la memoria persistente.

---

## ✨ Features

- 🎯 **SDD Flow completo** — 12 pasos: idea → spec → PRD → tasks → architecture → implementation → testing → review → commit → push → documentation → memory update
- 🤖 **7 agentes OpenCode** — Un orquestador que delega automáticamente a agentes especializados (backend, DB, testing, GitHub, review, documentación)
- 🗃️ **Trazabilidad total** — Cada proyecto, PRD, tarea y decisión se persiste en PostgreSQL con relaciones y metadatos
- 🐳 **PostgreSQL en Docker** — Base de datos aislada, reproducible, lista en segundos
- 🔌 **CLI global** — `lemoria` disponible en cualquier terminal tras la instalación
- 📂 **Proyectos independientes** — Cada proyecto vive en su propia carpeta, sin contaminación cruzada
- 📚 **Obsidian vault** — Documentación sincronizada opcional para edición visual
- 📋 **Decisiones registradas** — Cada cambio importante queda documentado como ADR antes de implementar

---

## 🚀 Quick Start

```bash
# 1. Clona el repositorio
git clone https://github.com/cristianl0pez-dev/lemoria.git && cd lemoria

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
lemoria project list              # Lista todos tus proyectos
lemoria flow list <project-id>    # PRDs del proyecto
lemoria task list <project-id>    # Tareas del proyecto
lemoria decision list <project-id> # Decisiones registradas
lemoria --help                    # Ayuda completa
```

---

## 📋 SDD Flow — Spec Driven Development

Lemoria implementa el flujo **SDD** en 12 pasos, donde cada etapa produce un artefacto que alimenta la siguiente:

```
💡 Idea
   │
   ↓
📐 Spec              → Especificación detallada
   │
   ↓
📄 PRD               → Product Requirements Document
   │
   ↓
📋 Tasks             → Desglose en tareas atómicas
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

### Principios SDD

| # | Principio |
|---|-----------|
| 1 | Toda implementación comienza con un **PRD** |
| 2 | Toda tarea se deriva de un **PRD o spec** |
| 3 | Todo commit referencia una **tarea** |
| 4 | Toda decisión se registra **antes** de implementar |
| 5 | La documentación se actualiza en **cada ciclo** |

---

## 🤖 Agentes OpenCode

Lemoria incluye **7 agentes** que se orquestan automáticamente. El `orchestrator` es el agente por defecto; los demás son subagentes a los que delega según la fase del flujo SDD.

| Agente | Modo | Rol |
|--------|------|-----|
| 🧠 **Orchestrator** | `primary` (default) | Decide el flujo SDD y asigna tareas a subagentes |
| 🖥️ **Backend Agent** | `subagent` | Implementación de código backend |
| 🗄️ **DB Agent** | `subagent` | Gestión de esquemas y modelos de base de datos |
| 🧪 **Testing Agent** | `subagent` | Escritura y ejecución de tests |
| 👁️ **Review Agent** | `subagent` | Revisión técnica de código y PRDs |
| 🐙 **GitHub Agent** | `subagent` | Trazabilidad GitHub: commits, PRs, issues |
| 📝 **Documentation Agent** | `subagent` | Documentación técnica y sincronización con Obsidian |

---

## 🗂️ Project Structure

```
lemoria/
├── lemoria/                  # CLI principal (Click)
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                # Punto de entrada CLI (Click commands)
│   ├── config.py             # Configuración vía pydantic-settings
│   ├── core.py               # Orquestador principal (Lemoria class)
│   ├── database.py           # Conexión y sesión SQLAlchemy
│   ├── flow.py               # Motor SDD (FlowEngine)
│   ├── git_service.py        # Servicio de commits/pushes
│   ├── memory.py             # Servicio de memoria (conversaciones)
│   ├── orchestrator.py       # Registro y delegación de agentes
│   ├── project.py            # CRUD de proyectos
│   └── vault.py              # Integración con Obsidian
├── database/                 # Capa de base de datos
│   ├── models/               # 15 modelos SQLAlchemy
│   │   ├── agent.py
│   │   ├── commit.py
│   │   ├── conversation.py
│   │   ├── decision.py
│   │   ├── prd.py
│   │   ├── project.py
│   │   ├── task.py
│   │   └── ... (8 más)
│   ├── migrations/           # Migraciones Alembic
│   └── seed/                 # Datos semilla
├── apps/                     # Aplicaciones modulares
│   ├── agents/
│   ├── github/
│   ├── memory/
│   ├── obsidian/
│   ├── orchestration/
│   ├── projects/
│   └── sdd/
├── docs/                     # Documentación
│   ├── ARCHITECTURE.md
│   ├── PRD.md
│   ├── ROADMAP.md
│   └── SDD.md
├── vault/                    # Obsidian vault (opcional)
├── .opencode/
│   ├── agents/               # Definiciones de los 7 agentes
│   └── skills/               # Skills Lemoria
├── tests/                    # Tests unitarios e integración
├── docker/                   # Dockerfile adicional
├── docker-compose.yml        # PostgreSQL 16
├── Dockerfile                # Imagen del proyecto
├── install.sh                # Instalación automatizada
├── pyproject.toml            # Configuración del proyecto
├── opencode.jsonc            # Configuración de OpenCode
├── alembic.ini               # Configuración de Alembic
├── INSTALL.md                # Guía de instalación detallada
├── index.html                # Landing page
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
| **Agentes** | [OpenCode](https://opencode.ai) (7 agentes) |
| **Vault** | [Obsidian](https://obsidian.md/) (opcional) |
| **Testing** | [pytest](https://pytest.org/) |
| **Linting** | [Ruff](https://docs.astral.sh/ruff/) |

---

## 📚 Documentación

| Recurso | Descripción |
|---------|-------------|
| [📖 INSTALL.md](INSTALL.md) | Instalación detallada paso a paso |
| [📄 PRD](docs/PRD.md) | Product Requirements Document |
| [🏗️ ARCHITECTURE](docs/ARCHITECTURE.md) | Arquitectura del sistema |
| [🗺️ ROADMAP](docs/ROADMAP.md) | Roadmap del proyecto |
| [📋 SDD](docs/SDD.md) | Spec Driven Development — flujo completo |

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

**MIT License** — Copyright © 2026 [Cristian López](https://github.com/cristianl0pez-dev)

Se concede permiso, sin cargo, a cualquier persona que obtenga una copia de este software y de los archivos de documentación asociados, para utilizarlo sin restricción, incluyendo sin limitación los derechos de usar, copiar, modificar, fusionar, publicar, distribuir, sublicenciar y/o vender copias del Software.

---

<p align="center">
  <sub>Hecho con ❤️ por <a href="https://github.com/cristianl0pez-dev">@cristianl0pez-dev</a></sub>
  <br>
  <sub>✨ Lemoria — Nunca olvides por qué escribes cada línea de código ✨</sub>
</p>
