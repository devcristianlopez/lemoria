# Lemoria

**Sistema Operativo de Memoria y Orquestación para Desarrollo con IA**

Lemoria es una plataforma local-first diseñada para asistir el desarrollo de software mediante memoria persistente, coordinación multiagente, trazabilidad técnica y desarrollo guiado por especificaciones (SDD).

## Stack

- **Backend:** Python
- **Base de Datos:** PostgreSQL
- **ORM:** SQLAlchemy
- **Agentes:** OpenCode Agents
- **Vault:** Obsidian
- **Versionado:** Git + GitHub

## Inicio rápido

```bash
# Iniciar PostgreSQL
docker compose up -d

# Instalar dependencias
pip install -e ".[dev]"

# Inicializar Lemoria
python -m lemoria init

# Crear un proyecto
python -m lemoria project create "mi-proyecto" --description "..."

# Iniciar flujo SDD
python -m lemoria flow start <project-id> "idea description"
```

## Estructura

```
lemoria/
├── apps/           # Módulos de aplicación
├── agents/         # Definiciones de agentes OpenCode
├── database/       # Modelos y migraciones
├── docs/           # Documentación del sistema
├── vault/          # Sincronización Obsidian
├── lemoria/        # Código fuente Python
├── docker/         # Configuración Docker
└── tests/          # Tests
```

## Documentación

- [PRD](docs/PRD.md) — Product Requirements Document
- [ARCHITECTURE](docs/ARCHITECTURE.md) — Arquitectura del sistema
- [ROADMAP](docs/ROADMAP.md) — Roadmap del proyecto
- [SDD](docs/SDD.md) — Spec Driven Development
