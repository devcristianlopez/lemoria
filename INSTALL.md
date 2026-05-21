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

El script te preguntará:

- **Global** — agentes disponibles en **cualquier proyecto** que abras con OpenCode
- **Proyecto** — agentes solo en esta carpeta (modo portable)

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

### 6. Elegir modo de instalación

#### Opción A: Global (recomendada)

Los agentes se copian a `~/.config/opencode/agents/` y la skill a `~/.config/opencode/skills/lemoria/`.

```bash
mkdir -p ~/.config/opencode/{agents,skills/lemoria}
cp .opencode/agents/* ~/.config/opencode/agents/
cp .opencode/skills/lemoria/SKILL.md ~/.config/opencode/skills/lemoria/
```

Crea `~/.config/opencode/opencode.json`:

```json
{
  "default_agent": "orchestrator",
  "skills": {
    "paths": ["~/.config/opencode/skills"]
  }
}
```

Ahora abre **cualquier proyecto** con `opencode` y los agentes estarán disponibles.

#### Opción B: Solo proyecto

Los agentes quedan en `.opencode/agents/` local. Debes abrir OpenCode desde esta carpeta:

```bash
opencode .
```

## Uso

```bash
# Crear proyecto
lemoria project create "mi-proyecto"
lemoria flow start <project-id> "descripción de la idea"
lemoria agent list
```

## Notas

- PostgreSQL debe estar **siempre corriendo** (docker compose tiene `restart: unless-stopped`)
- En modo global, los agentes se auto-descubren desde `~/.config/opencode/agents/`
- El vault `vault/obsidian/` se puede abrir con Obsidian
- **GitHub CLI (`gh`)** es opcional. Sin él, el github-agent usa git manual sin PRs automáticos. Instálalo desde [cli.github.com](https://cli.github.com/)
