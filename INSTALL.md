# Instalación de Lemoria

## Requisitos

- **Python** >= 3.11 + pip
- **Docker** + **Docker Compose**
- **OpenCode** (para usar agentes)
- **Obsidian** (opcional, visualizar vault)

## Instalación rápida

```bash
git clone https://github.com/cristianl0pez-dev/lemoria.git
cd lemoria
chmod +x install.sh
./install.sh
```

Tras la instalación, `lemoria` es un comando global. Abre **OpenCode** desde el directorio del proyecto y ya puedes crear proyectos.

## Instalación paso a paso

### 1. Clonar

```bash
git clone https://github.com/cristianl0pez-dev/lemoria.git
cd lemoria
```

### 2. Configurar entorno

```bash
cp .env.example .env
```

### 3. Iniciar PostgreSQL

```bash
docker compose up -d
```

### 4. Instalar Lemoria globalmente

```bash
pip install --user -e ".[dev]"
export PATH="$PATH:$HOME/.local/bin"
```

### 5. Inicializar

```bash
lemoria init
```

### 6. Abrir OpenCode

```bash
opencode
```

Desde OpenCode puedes:
- Usar los comandos `@lemoria-init`, `@lemoria-project`, `@lemoria-flow`, `@lemoria-agent`
- Invocar los agentes: orchestrator, backend-agent, db-agent, testing-agent, github-agent, review-agent, documentation-agent
- Ejecutar `lemoria` directamente en la terminal

## Estructura OpenCode

```
lemoria/
├── .opencode/
│   ├── agents/          # Agentes OpenCode (auto-descubiertos)
│   └── skills/
│       └── lemoria/     # Skill de Lemoria
├── opencode.jsonc       # Config principal
└── ...
```

## Uso desde OpenCode

```bash
# Crear proyecto
lemoria project create "mi-proyecto" -d "Descripción"

# Iniciar flujo SDD
lemoria flow start <project-id> "descripción de la idea"

# Listar agentes
lemoria agent list
```

## Notas

- PostgreSQL debe estar **siempre corriendo** (docker compose tiene `restart: unless-stopped`)
- Los agentes están en `.opencode/agents/` con modo `subagent`
- El vault `vault/obsidian/` se puede abrir con Obsidian
