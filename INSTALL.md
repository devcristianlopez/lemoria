# Instalación de Lemoria

## Importante: Lemoria se instala una vez, tus proyectos van aparte

```
┌──────────────────────────────────────────────────┐
│  lemoria/ (este repo)                            │
│  Solo para INSTALAR. Después puedes borrarlo.    │
└──────────────────────────────────────────────────┘
                        ↓
              instala globalmente:
              • comando `lemoria`
               • 8 agentes en ~/.config/opencode/agents/
              • PostgreSQL en Docker
                        ↓
┌──────────────────────────────────────────────────┐
│  ~/mi-proyecto/ (carpeta vacía para tu código)   │
│  Abres OpenCode aquí y los agentes globales      │
│  están disponibles automáticamente.              │
└──────────────────────────────────────────────────┘
```

## Requisitos

- **Python** >= 3.11 + pip
- **Docker** + **Docker Compose**
- **OpenCode** (CLI)
- **Obsidian** (opcional)
- **GitHub CLI `gh`** (opcional, para PRs automáticos)

## Instalación (una sola vez)

```bash
git clone https://github.com/devcristianlopez/lemoria.git
cd lemoria
chmod +x install.sh
./install.sh
```

El script pregunta:

- **1) Global (recomendada)** — agentes disponibles en **cualquier proyecto** que abras con OpenCode
- **2) Proyecto** — agentes solo dentro de la carpeta `lemoria/`

Elige **1) Global**.

### Qué hace el instalador

| Paso | Acción |
|------|--------|
| 1 | Verifica Python, Docker |
| 2 | Crea `.env` |
| 3 | Levanta PostgreSQL en Docker |
| 4 | Instala `lemoria` como comando global (`pip install --user`) |
| 5 | Inicializa la base de datos |
| 6 | Copia agentes y skills a `~/.config/opencode/` |
| 7 | Configura Context7 MCP (documentación en tiempo real para librerías) |
| 8 | Crea `~/.config/opencode/opencode.json` con `default_agent: orchestrator` |

### Después de instalar

```bash
# Verifica que lemoria funciona (desde cualquier directorio)
lemoria --help

# Verifica que PostgreSQL está corriendo
docker ps | grep lemoria-db

# El repo lemoria/ ya no hace falta, puedes borrarlo:
# rm -rf ~/lemoria
```

## Cómo crear un proyecto

```bash
# 1. Crea una carpeta vacía para tu proyecto
mkdir ~/mi-aplicacion
cd ~/mi-aplicacion

# 2. Inicializa git si quieres
git init

# 3. Abre OpenCode
opencode
```

Los agentes globales están disponibles inmediatamente. El orquestador responde a cualquier feature request:

```
Tú: "quiero un endpoint POST /login con JWT"
→ Orchestrator ejecuta el flujo SDD completo
→ Crea proyecto en PostgreSQL, conversación, PRD, tareas
→ Delega a implementation-agent, frontend-agent, testing-agent, review-agent...
→ Todo queda registrado con trazabilidad
```

## Instalación paso a paso (sin el script)

```bash
# 1. Clonar
git clone https://github.com/devcristianlopez/lemoria.git
cd lemoria

# 2. Configurar
cp .env.example .env

# 3. PostgreSQL
docker compose up -d

# 4. Instalar comando global
pip install --user -e ".[dev]"
export PATH="$PATH:$HOME/.local/bin"

# 5. Inicializar DB
lemoria init

# 6. Copiar agentes y skills a global
mkdir -p ~/.config/opencode/{agents,skills/lemoria}
cp .opencode/agents/*.md ~/.config/opencode/agents/
cp .opencode/skills/lemoria/SKILL.md ~/.config/opencode/skills/lemoria/
cp -r .opencode/skills/{frontend,backend,database,testing,code-review,git-workflow,documentation} ~/.config/opencode/skills/

# 7. Crear config global
cat > ~/.config/opencode/opencode.json <<- 'EOF'
{
  "default_agent": "orchestrator",
  "skills": {
    "paths": ["~/.config/opencode/skills"]
  }
}
EOF

# 8. Instalar Context7 MCP (documentación en tiempo real)
npx -y ctx7 setup --opencode --mcp

# 9. Listo. El repo lemoria/ ya no es necesario
cd ~
rm -rf lemoria  # opcional
```

## Comandos básicos (funcionan desde cualquier lado)

```bash
lemoria project create "mi-api" -d "API REST"
lemoria project list
lemoria conv create <project-id> -t "Feature: login"
lemoria conv add <conv-id> user "descripción"
lemoria flow start <project-id> "sistema de auth"
lemoria flow list <project-id>
lemoria task create <project-id> <prd-id> -t "modelo User"
lemoria task list <project-id>
lemoria decision log <project-id> -t "usar JWT" -d "stateless"
lemoria agent list
```

## Notas

- PostgreSQL corre en Docker con `restart: unless-stopped` (siempre activo)
- Sin `gh` (GitHub CLI) el github-agent usa git manual
- El vault para Obsidian se configura por proyecto en `.env`
