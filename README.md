# Lemoria

**Sistema Operativo de Memoria y Orquestación para Desarrollo con IA**

Plataforma local-first para desarrollo asistido por IA con memoria persistente, coordinación multiagente, trazabilidad técnica y desarrollo guiado por especificaciones (SDD).

## Stack

- **Backend:** Python / SQLAlchemy
- **Base de Datos:** PostgreSQL (Docker)
- **Agentes:** OpenCode Agents
- **Vault:** Obsidian (opcional)
- **Versionado:** Git + GitHub

## Instalación

```bash
git clone https://github.com/cristianl0pez-dev/lemoria.git
cd lemoria
chmod +x install.sh
./install.sh
```

Ver [INSTALL.md](INSTALL.md) para instalación paso a paso.

## Uso

`lemoria` se instala como comando global:

```bash
# Crear proyecto
lemoria project create "mi-proyecto"

# Iniciar flujo SDD
lemoria flow start <project-id> "descripción de la idea"

# Ver agentes
lemoria agent list
```

## Estructura

```
lemoria/
├── agents/         # Definiciones de agentes OpenCode
├── database/       # Modelos SQLAlchemy
├── docs/           # Documentación del sistema
├── lemoria/        # Código fuente Python
├── vault/          # Sincronización Obsidian
├── docker-compose.yml
├── opencode.jsonc
├── INSTALL.md
└── install.sh
```
