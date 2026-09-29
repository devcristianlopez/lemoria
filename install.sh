#!/usr/bin/env bash
set -euo pipefail

LEMORIA_DIR="$(cd "$(dirname "$0")" && pwd)"
LEMORIA_VAULT_DIR="$HOME/.lemoria/vault"
cd "$LEMORIA_DIR"

echo "========================================"
echo "  Lemoria — Instalación automatizada"
echo "========================================"
echo ""

# ----- Verificar requisitos -----
echo "[1/9] Verificando requisitos..."

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 no encontrado"; exit 1; }
echo "  python3 : $(python3 --version)"

# Postgres: Docker ya no es obligatorio. What matters is whether something
# answers on the TCP port the app connects to -- pg_isready with no host only
# checks the Unix socket, which says nothing about a container or a server
# listening on TCP alone.
DB_PORT="${LEMORIA_DB_PORT:-5432}"
if command -v pg_isready >/dev/null 2>&1 && pg_isready -h localhost -p "$DB_PORT" -q 2>/dev/null; then
    PG_READY=true
else
    PG_READY=false
fi
DOCKER_AVAILABLE=false
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    DOCKER_AVAILABLE=true
fi

if $PG_READY; then
    echo "  postgres: ya responde en localhost:$DB_PORT"
elif $DOCKER_AVAILABLE; then
    echo "  postgres: via Docker (aún no levantado)"
else
    echo "  postgres: NO ENCONTRADO"
    echo ""
    echo "  Lemoria necesita PostgreSQL. Instala uno de los dos:"
    echo "    • Arch/Manjaro: sudo pacman -S postgresql && sudo systemctl enable --now postgresql"
    echo "    • Docker:      instala Docker y vuelve a correr este script"
    echo ""
    # Llegar acá significa que tampoco hay Docker, así que no hay nada que
    # intentar: preguntar "¿lo intentamos con Docker?" sería una pregunta falsa.
    echo "Abortado. Instala PostgreSQL (o Docker) y vuelve a correr ./install.sh"
    exit 1
fi

GH_AVAILABLE=false
if command -v gh >/dev/null 2>&1; then
    GH_AVAILABLE=true
    echo "  gh      : $(gh --version 2>&1 | head -1)"
else
    echo "  gh      : no instalado (opcional)"
fi
echo "  OK"

# ----- Elegir modo de instalación -----
echo ""
echo "¿Cómo quieres instalar los agentes de Lemoria?"
echo ""
echo "  1) Global  — Los agentes disponibles en CUALQUIER proyecto que abras con OpenCode"
echo "               (se copian a ~/.config/opencode/agents/)"
echo ""
echo "  2) Proyecto — Los agentes solo funcionan dentro de esta carpeta"
echo "               (modo portable, .opencode/ local)"
echo ""
read -rp "Selecciona [1/2] (default: 1): " INSTALL_MODE
INSTALL_MODE="${INSTALL_MODE:-1}"
echo ""

# ----- .env -----
echo "[2/9] Configurando .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  .env creado desde .env.example"
else
    echo "  .env ya existe, se mantiene"
fi

# Read one key out of .env. Deliberately NOT `source .env`: that executes
# whatever is in the file, and an installer should not run code it just
# copied from a repository. Parse the line instead.
env_value() {
    local key="$1" fallback="$2" line value
    line="$(grep -E "^${key}=" .env 2>/dev/null | tail -1)" || true
    if [ -z "$line" ]; then
        printf '%s' "$fallback"
        return
    fi
    value="${line#*=}"
    # Strip matching surrounding quotes. Quoted values keep their inner spaces;
    # unquoted ones lose an inline comment and get trimmed, so a trailing
    # space in a password can't survive and break the connection silently.
    case "$value" in
        \"*\") value="${value#\"}"; value="${value%\"}" ;;
        \'*\') value="${value#\'}"; value="${value%\'}" ;;
        *)
            value="${value%%[[:space:]]#*}"
            value="${value#"${value%%[![:space:]]*}"}"
            value="${value%"${value##*[![:space:]]}"}"
            ;;
    esac
    printf '%s' "$value"
}

DB_USER="$(env_value LEMORIA_DB_USER lemoria)"
DB_PASSWORD="$(env_value LEMORIA_DB_PASSWORD lemoria)"
DB_NAME="$(env_value LEMORIA_DB_NAME lemoria)"
# An env var from the caller still wins: it is explicit, the file is default.
DB_USER="${LEMORIA_DB_USER:-$DB_USER}"
DB_PASSWORD="${LEMORIA_DB_PASSWORD:-$DB_PASSWORD}"
DB_NAME="${LEMORIA_DB_NAME:-$DB_NAME}"

# ----- Docker Compose -----
echo "[3/9] Configurando PostgreSQL..."
if $PG_READY; then
    # Algo ya responde en el puerto y no es asunto nuestro. El instalador no
    # administra servidores que ya estaban corriendo: solo verifica que la
    # credenciales de .env sirvan, y avisa con precisión si no.
    if ! command -v psql >/dev/null 2>&1; then
        echo "  PostgreSQL responde en localhost:$DB_PORT y no se tocó."
        echo "  No encontré 'psql', así que no pude verificar las credenciales."
        echo "  Si Lemoria falla al conectar, revisá LEMORIA_DB_* en .env."
    elif PGPASSWORD="$DB_PASSWORD" psql \
        -h localhost -p "$DB_PORT" \
        -U "$DB_USER" -d "$DB_NAME" \
        -tAc "SELECT 1" >/dev/null 2>&1; then
        echo "  PostgreSQL ya responde en localhost:$DB_PORT — no se tocó"
        echo "  Credenciales de .env válidas ($DB_USER@localhost/$DB_NAME)"
    else
        echo "  ! PostgreSQL responde en localhost:$DB_PORT pero las credenciales"
        echo "    de .env no sirven. Ajusta LEMORIA_DB_* y reintenta, o crea la"
        echo "    base a mano. El instalador no administra este servidor."
    fi
else
    docker compose up -d
    echo "  Esperando que PostgreSQL esté saludable..."
    until docker compose exec db pg_isready -U lemoria >/dev/null 2>&1; do
        sleep 1
    done
    echo "  PostgreSQL (Docker) listo"
fi

# ----- Instalar Lemoria como comando global -----
echo "[4/9] Instalando Lemoria como comando global..."

install_with_pip() {
    python3 -m pip install --user -q -e "$LEMORIA_DIR[dev]" 2>/dev/null || \
    python3 -m pip install -q -e "$LEMORIA_DIR[dev]" 2>/dev/null
}

install_with_venv() {
    local VENV_DIR="$HOME/.local/share/lemoria/venv"
    echo "  Creando venv en $VENV_DIR ..."
    python3 -m venv "$VENV_DIR" || {
        echo "ERROR: no se pudo crear el venv. Instalá python3-venv:"
        echo "  sudo apt install python3-venv python3-full"
        return 1
    }
    echo "  Instalando dependencias en el venv..."
    "$VENV_DIR/bin/pip" install -q -e "$LEMORIA_DIR[dev]" || {
        echo "ERROR: falló la instalación en el venv."
        return 1
    }
    mkdir -p "$HOME/.local/bin"
    ln -sf "$VENV_DIR/bin/lemoria" "$HOME/.local/bin/lemoria"
    echo "  ✓ Lemoria instalado en venv propio"
    echo "  ✓ Comando disponible en ~/.local/bin/lemoria"
}

if install_with_pip; then
    echo "  Dependencias instaladas (pip)"
else
    echo "  pip system-wide no disponible (entorno externamente gestionado / PEP 668)"
    echo "  Usando venv propio como alternativa..."
    if install_with_venv; then
        echo "  Instalación en venv completada"
    else
        echo ""
        echo "  ERROR: No se pudo instalar Lemoria."
        echo "  Soluciones:"
        echo "    1) Instalá python3-venv: sudo apt install python3-venv python3-full"
        echo "    2) O usá pipx: sudo apt install pipx && pipx install lemoria"
        echo "    3) O forzá la instalación: pip install --break-system-packages -e ."
        exit 1
    fi
fi

LOCAL_BIN="$HOME/.local/bin"
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    SHELL_CONFIG=""
    case "$SHELL" in
        */zsh) SHELL_CONFIG="$HOME/.zshrc" ;;
        */bash) SHELL_CONFIG="$HOME/.bashrc" ;;
    esac
    if [ -n "$SHELL_CONFIG" ]; then
        echo "export PATH=\"\$PATH:$LOCAL_BIN\"" >> "$SHELL_CONFIG"
        echo "  $LOCAL_BIN agregado al PATH en $SHELL_CONFIG"
    fi
fi
export PATH="$PATH:$LOCAL_BIN"

echo "  Lemoria instalado globalmente: $(command -v lemoria || echo 'recarga tu terminal')"

# ----- Inicializar -----
echo "[5/9] Inicializando Lemoria..."
lemoria init
echo "  Base de datos inicializada"
echo "  Vault listo en $LEMORIA_VAULT_DIR/"
echo "  (memoria privada — mantenla fuera de tus repos git)"

# ----- Configurar OpenCode -----
OPENCODE_GLOBAL_DIR="$HOME/.config/opencode"

if [ "$INSTALL_MODE" = "1" ]; then
    echo "[6/9] Instalando agentes en modo GLOBAL..."

    mkdir -p "$OPENCODE_GLOBAL_DIR/agents"
    mkdir -p "$OPENCODE_GLOBAL_DIR/skills"
    for skill_dir in lemoria frontend backend database testing code-review git-workflow documentation; do
        if [ -d ".opencode/skills/$skill_dir" ]; then
            mkdir -p "$OPENCODE_GLOBAL_DIR/skills/$skill_dir"
            cp ".opencode/skills/$skill_dir/SKILL.md" "$OPENCODE_GLOBAL_DIR/skills/$skill_dir/"
        fi
    done

    cp .opencode/agents/*.md "$OPENCODE_GLOBAL_DIR/agents/"
    echo "  Agentes copiados a $OPENCODE_GLOBAL_DIR/agents/"
    echo "  Skills copiados a $OPENCODE_GLOBAL_DIR/skills/"

    if [ ! -f "$OPENCODE_GLOBAL_DIR/opencode.json" ]; then
        cat > "$OPENCODE_GLOBAL_DIR/opencode.json" <<- 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "orchestrator",
  "skills": {
    "paths": ["~/.config/opencode/skills"]
  }
}
EOF
        echo "  Config global creada: $OPENCODE_GLOBAL_DIR/opencode.json"
    else
        echo "  Config global ya existe: $OPENCODE_GLOBAL_DIR/opencode.json (no se modifica)"
        echo "  Asegúrate de que incluya:"
        echo '    "default_agent": "orchestrator"'
        echo '    "skills": { "paths": ["~/.config/opencode/skills"] }'
    fi
    echo ""
    echo "  ✓ Agentes disponibles en cualquier proyecto al abrir OpenCode"
else
    echo "[6/9] Instalación en modo PROYECTO..."
    # Los .md ya estan en .opencode/agents del repo; lo que falta es el config
    # local apuntando al orquestador, porque no viene por defecto.
    if [ ! -f "$LEMORIA_DIR/opencode.jsonc" ]; then
        cat > "$LEMORIA_DIR/opencode.jsonc" <<- 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "orchestrator",
  "skills": { "paths": [".opencode/skills"] }
}
EOF
        echo "  Config local creado: opencode.jsonc"
    else
        echo "  Config local ya existe: opencode.jsonc (no se modifica)"
        echo '  Asegúrate de que incluya: "default_agent": "orchestrator"'
    fi
    echo "  Agentes en .opencode/agents/ (solo dentro de este proyecto)"
    echo "  Abre OpenCode desde esta carpeta para usarlos"
fi

# ----- Context7 (documentation MCP) -----
echo ""
echo "[7/9] Context7 — documentación actualizada para librerías..."
echo ""
echo "  Context7 es un MCP server que provee documentación actualizada"
echo "  de React, Next.js, Prisma, Tailwind, etc. directamente al agente."
echo ""
echo "  ¿Quieres instalar Context7?"
echo "  (requiere Node.js — npx — para ejecutarse)"
echo ""
read -rp "  Instalar? [s/N]: " INSTALL_CTX7
if [ "${INSTALL_CTX7:-n}" = "s" ] || [ "${INSTALL_CTX7:-n}" = "S" ]; then
    echo ""
    echo "  Instalando Context7 MCP..."
    if command -v npx >/dev/null 2>&1; then
        npx -y ctx7 setup --opencode --mcp 2>&1 && \
            echo "  ✓ Context7 instalado y configurado" || \
            echo "  ✗ Falló instalación de Context7 (puedes hacerlo después: npx ctx7 setup --opencode --mcp)"
    else
        echo "  npx no encontrado. Salta este paso."
        echo "  Instala Node.js primero, luego: npx ctx7 setup --opencode --mcp"
    fi
else
    echo "  Saltado. Puedes instalar después: npx ctx7 setup --opencode --mcp"
fi

# ----- Integraciones del entorno -----
# What Lemoria can wire up depends on what this machine actually has: the
# Omarchy panel only exists on Omarchy, and telemetry only exists if opencode
# has a database to read. Neither is required to install.
echo ""
echo "[8/9] Detectando tu entorno..."

OMARCHY_AVAILABLE=false
if [ -n "${OMARCHY_PATH:-}" ] || [ -d /usr/share/omarchy ]; then
    OMARCHY_AVAILABLE=true
fi

OPENCODE_DB="${XDG_DATA_HOME:-$HOME/.local/share}/opencode/opencode.db"
OPENCODE_AVAILABLE=false
[ -f "$OPENCODE_DB" ] && OPENCODE_AVAILABLE=true

# Register the agents. The .md files are the source of truth, so this mirrors
# them into the database rather than the other way around.
echo "  Registrando agentes en la base de datos..."
if lemoria agent sync 2>&1 | sed 's/^/    /'; then
    echo "  ✓ Agentes sincronizados"
else
    echo "  ! El sync falló. Revisa con: lemoria agent sync"
fi

PANEL_INSTALLED=false
if $OMARCHY_AVAILABLE; then
    echo ""
    echo "  Detectado Omarchy. Publicar el consumo en su panel de agentes"
    echo "  (tokens por día y por modelo, histórico completo) más un timer"
    echo "  de usuario que lo refresca cada minuto."
    echo ""
    # Default yes: on Omarchy the panel is the whole point of this branch, and
    # "no" should be the thing you have to ask for. It only writes a user-level
    # record and timer, both reversible with `lemoria omarchy uninstall`.
    read -rp "  ¿Instalar el panel? [S/n]: " USE_PANEL
    if [ "${USE_PANEL:-s}" != "n" ] && [ "${USE_PANEL:-N}" != "N" ]; then
        if lemoria omarchy install 2>&1 | sed 's/^/    /'; then
            PANEL_INSTALLED=true
            echo "  ✓ Panel de Omarchy conectado (se refresca cada 1 min)"
        else
            echo "  ✗ No se pudo instalar el panel. Reintenta con: lemoria omarchy install"
        fi
    else
        echo "  Saltado. Conéctalo después con: lemoria omarchy install"
    fi
else
    echo "  Omarchy no detectado: no se instala el panel."
    echo "  Todo lo que el panel muestra está disponible en: lemoria usage"
fi

if $OPENCODE_AVAILABLE; then
    echo "  ✓ Telemetría activa (lectura de opencode.db)"
else
    echo "  ! No encontré opencode.db en $OPENCODE_DB"
    echo "    Sin él, 'lemoria usage' y el panel no tienen datos que mostrar."
    echo "    Se activa solo cuando uses opencode: la telemetría no se configura."
fi

# ----- Resumen -----
echo ""
echo "[9/9] Instalación completada"
echo ""
echo "============================================"
echo "  Lemoria está listo"
echo "============================================"
echo ""
echo "  Usa 'lemoria' desde cualquier terminal:"
echo ""
echo "    lemoria project create \"mi-proyecto\""
echo "    lemoria agent list"
echo "    lemoria --help"
echo ""
if [ "$INSTALL_MODE" = "1" ]; then
echo "  Los agentes están disponibles GLOBALMENTE."
echo "  Abre OpenCode en cualquier proyecto y usa:"
echo "    @orchestrator, @implementation-agent, @frontend-agent, ..."
else
echo "  Los agentes están disponibles solo en este proyecto."
echo "  Abre OpenCode desde esta carpeta: opencode ."
fi
echo ""
if [ "$GH_AVAILABLE" = false ]; then
echo "  gh (GitHub CLI) no detectado. El github-agent usará git manual."
echo "  Para crear PRs y gestionar repos: https://cli.github.com/"
echo ""
fi
echo "  Skills disponibles:"
echo "    frontend, backend, database, testing, code-review, git-workflow, documentation"
echo ""
echo "  Para abrir Obsidian vault:"
    echo "    obsidian $LEMORIA_VAULT_DIR"
    echo ""
    if $PG_READY; then
echo "  PostgreSQL ya estaba corriendo en localhost:$DB_PORT — no se tocó."
    echo "  Para detenerlo:"
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q postgresql; then
        echo "    sudo systemctl stop postgresql"
    else
        echo "    docker compose down   (o el comando con que lo levantaste)"
    fi
else
echo "  Para detener PostgreSQL:"
    echo "    docker compose down"
fi
echo ""
echo "  Consumo de opencode:"
if $PANEL_INSTALLED; then
echo "    • En el panel de Omarchy (pestaña 'Lemoria')"
echo "    • Texto plano:  lemoria usage"
echo "    • estructurado: lemoria usage --json"
elif $OMARCHY_AVAILABLE; then
echo "    • Texto plano:  lemoria usage"
echo "    • estructurado: lemoria usage --json"
echo "    • Panel:        lemoria omarchy install  (no lo instalaste)"
else
echo "    lemoria usage          # total, por modelo, por agente, 7 días"
echo "    lemoria usage --json   # lo mismo, estructurado"
fi
echo ""
echo "  Para fijar el modelo de un agente (opcional, hereda por defecto):"
echo "    lemoria agent model implementation-agent <modelo> -v <effort>"
echo "    lemoria agent model implementation-agent --clear   # volver a heredar"
echo ""
