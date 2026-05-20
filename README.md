# Lemoria

**Sistema Operativo de Memoria y Orquestación para Desarrollo con IA**

Plataforma local-first para desarrollo asistido por IA con memoria persistente, coordinación multiagente y trazabilidad técnica.

## Stack

- **Backend:** Python / SQLAlchemy
- **Base de Datos:** PostgreSQL (Docker)
- **Agentes:** OpenCode (subagentes en `.opencode/agents/`)
- **Vault:** Obsidian (opcional)

## Instalación

```bash
git clone https://github.com/cristianl0pez-dev/lemoria.git
cd lemoria
chmod +x install.sh
./install.sh
opencode
```

Ver [INSTALL.md](INSTALL.md) para instalación detallada.

## Uso

```bash
lemoria project create "mi-proyecto"
lemoria flow start <id> "idea"
lemoria agent list
```

## Agentes OpenCode

| Agente | Rol |
|--------|-----|
| orchestrator | Orquestador (analiza contexto, delega) |
| backend-agent | Implementación backend |
| db-agent | Gestión de base de datos |
| testing-agent | Tests y calidad |
| github-agent | Trazabilidad GitHub |
| review-agent | Revisión técnica |
| documentation-agent | Documentación y Obsidian |

## Documentación

- [PRD](docs/PRD.md) — Product Requirements Document
- [ARCHITECTURE](docs/ARCHITECTURE.md) — Arquitectura del sistema
- [ROADMAP](docs/ROADMAP.md) — Roadmap del proyecto
- [SDD](docs/SDD.md) — Spec Driven Development
