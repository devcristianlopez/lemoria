#!/usr/bin/env bash
set -euo pipefail

LEMORIA_DIR="$(cd "$(dirname "$0")" && pwd)"
LEMORIA_VAULT_DIR="$HOME/.lemoria/vault"
cd "$LEMORIA_DIR"

# Las decisiones (qué base usar, qué instalador probar, qué paquete recomendar en
# cada distro) viven en installer/lib.sh para poder testearlas: install.sh es lineal,
# pide prompts y escribe en $HOME, así que no se puede correr dentro de un test.
# Acá solo se cargan las funciones.
# shellcheck source=installer/lib.sh
source "$LEMORIA_DIR/installer/lib.sh"

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
DB_PORT="$(resolve_db_port)"
detect_postgres
# Docker lleva dos flags porque tiene dos formas distintas de fallar, y el
# detalle de por qué el probe del daemon es 'docker info' y no
# 'docker compose version' está en detect_docker(), en installer/lib.sh.
detect_docker

if $DOCKER_BINARIO; then
    if $DOCKER_USABLE; then
        echo "  docker   : $(docker --version 2>/dev/null || echo 'instalado') — daemon responde"
    else
        echo "  docker   : $(docker --version 2>/dev/null || echo 'instalado') — daemon NO responde"
    fi
else
    echo "  docker   : no instalado (opcional)"
fi

if $PG_READY; then
    echo "  postgres: ya responde en localhost:$DB_PORT"
elif $DOCKER_USABLE; then
    echo "  postgres: via Docker (aún no levantado)"
else
    # Llegar acá significa que no hay servidor. La guía explica las dos vías
    # en vez de una línea suelta: la diferencia entre "no tenés Docker" y "tenés
    # Docker y no lo podés usar" es justo lo que el usuario no puede ver solo.
    echo "  postgres: NO ENCONTRADO"
    print_postgres_setup_guide
    echo ""
    echo "Abortado. Instala PostgreSQL y vuelve a correr ./install.sh"
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

DB_USER="$(env_value LEMORIA_DB_USER lemoria)"
DB_PASSWORD="$(env_value LEMORIA_DB_PASSWORD lemoria)"
DB_NAME="$(env_value LEMORIA_DB_NAME lemoria)"
# An env var from the caller still wins: it is explicit, the file is default.
DB_USER="${LEMORIA_DB_USER:-$DB_USER}"
DB_PASSWORD="${LEMORIA_DB_PASSWORD:-$DB_PASSWORD}"
DB_NAME="${LEMORIA_DB_NAME:-$DB_NAME}"

# ----- Docker Compose -----
echo "[3/9] Configurando PostgreSQL..."
# provide_postgres() deja la base andando y anota en DB_PROVIDER de dónde salió,
# para que el resumen final no tenga que adivinarlo.
provide_postgres "$DB_PORT" "$DB_USER" "$DB_PASSWORD" "$DB_NAME" || exit 1

echo "[4/9] Instalando Lemoria como comando global..."

# uv → venv → pip, en ese orden. Cada uno de los tres vive en installer/lib.sh:
# son los caminos que se prueban cuando los dos anteriores fallan.
if ! choose_installer; then
    echo ""
    echo "  ERROR: no se pudo instalar Lemoria por ninguno de los tres caminos"
    echo "  (uv → venv → pip). En orden de preferencia:"
    echo ""
    echo "    1) uv (recomendado, no pide sudo ni toca el sistema):"
    echo "         $(uv_install_hint)"
    echo "         uv tool install --editable \"$LEMORIA_DIR[dev]\""
    echo ""
    echo "    2) venv propio (si preferís no instalar uv):"
    echo "         $(pkg_hint python python3-venv)"
    echo "         python3 -m venv ~/.local/share/lemoria/venv"
    echo "         ~/.local/share/lemoria/venv/bin/pip install -e \"$LEMORIA_DIR[dev]\""
    echo ""
    echo "    3) pipx (otra variante de aislamiento):"
    echo "         $(pkg_hint python-pipx pipx)"
    echo ""
    echo "    Forzar sobre el intérprete del sistema solo como último recurso:"
    echo "      pip install --break-system-packages -e ."
    echo "      eso desactiva la protección PEP 668 y puede romper otras herramientas."
    exit 1
fi

echo "  ✓ Lemoria instalado vía: $INSTALLER"

LOCAL_BIN="$HOME/.local/bin"

# El PATH tiene que cubrir los dos destinos posibles: ~/.local/bin para venv y
# pip, y el directorio propio de uv cuando UV_TOOL_BIN_DIR lo apunta a otro
# lado. El resto del script llama a `lemoria init` y `lemoria agent sync`, así
# que si el ejecutable queda fuera del PATH el instalador se rompe igual.
if [ -n "${UV_BIN_DIR:-}" ] && [ "$UV_BIN_DIR" != "$LOCAL_BIN" ]; then
    export PATH="$PATH:$UV_BIN_DIR"
fi

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
    mkdir -p "$OPENCODE_GLOBAL_DIR/commands"
    for skill_dir in lemoria frontend backend database testing code-review git-workflow documentation; do
        if [ -d ".opencode/skills/$skill_dir" ]; then
            mkdir -p "$OPENCODE_GLOBAL_DIR/skills/$skill_dir"
            cp ".opencode/skills/$skill_dir/SKILL.md" "$OPENCODE_GLOBAL_DIR/skills/$skill_dir/"
        fi
    done

    cp .opencode/agents/*.md "$OPENCODE_GLOBAL_DIR/agents/"
    if compgen -G ".opencode/commands/*.md" >/dev/null; then
        cp .opencode/commands/*.md "$OPENCODE_GLOBAL_DIR/commands/"
    fi
    echo "  Agentes copiados a $OPENCODE_GLOBAL_DIR/agents/"
    echo "  Skills copiados a $OPENCODE_GLOBAL_DIR/skills/"
    echo "  Comandos copiados a $OPENCODE_GLOBAL_DIR/commands/"

    if [ ! -f "$OPENCODE_GLOBAL_DIR/opencode.json" ]; then
        cat > "$OPENCODE_GLOBAL_DIR/opencode.json" <<- 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "orchestrator",
  "skills": ["~/.config/opencode/skills"]
}
EOF
        echo "  Config global creada: $OPENCODE_GLOBAL_DIR/opencode.json"
    else
        echo "  Config global ya existe: $OPENCODE_GLOBAL_DIR/opencode.json (no se modifica)"
        echo "  Asegúrate de que incluya:"
        echo '    "default_agent": "orchestrator"'
        echo '    "skills": ["~/.config/opencode/skills"]'
    fi
    echo ""
    echo "  ✓ Agentes y comandos disponibles en cualquier proyecto al abrir OpenCode"
    echo "  Usa /lemoria desde el prompt de OpenCode para iniciar el flujo SDD."
else
    echo "[6/9] Instalación en modo PROYECTO..."
    # Los .md ya estan en .opencode/agents del repo; lo que falta es el config
    # local apuntando al orquestador, porque no viene por defecto.
    if [ ! -f "$LEMORIA_DIR/opencode.jsonc" ]; then
        cat > "$LEMORIA_DIR/opencode.jsonc" <<- 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "orchestrator",
  "skills": [".opencode/skills"]
}
EOF
        echo "  Config local creado: opencode.jsonc"
    else
        echo "  Config local ya existe: opencode.jsonc (no se modifica)"
        echo '  Asegúrate de que incluya: "default_agent": "orchestrator"'
    fi
    echo "  Agentes en .opencode/agents/ y comandos en .opencode/commands/"
    echo "  Abre OpenCode desde esta carpeta para usarlos; usa /lemoria en el prompt."
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
    echo "  Detectado Omarchy. Instalar el widget propio de Lemoria"
    echo "  (total en la barra, presupuesto, 7 días y agentes) más un timer"
    echo "  de usuario que refresca su record privado cada minuto."
    echo ""
    # Default yes: on Omarchy the widget is the whole point of this branch, and
    # "no" should be the thing you have to ask for. It only writes user-level
    # files: plugin, private record and timer, reversible with uninstall.
    read -rp "  ¿Instalar el panel? [S/n]: " USE_PANEL
    if [ "${USE_PANEL:-s}" != "n" ] && [ "${USE_PANEL:-N}" != "N" ]; then
        if lemoria omarchy install 2>&1 | sed 's/^/    /'; then
            PANEL_INSTALLED=true
            echo "  ✓ Widget Lemoria para Omarchy conectado (se refresca cada 1 min)"
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
print_db_stop_hint "$DB_PROVIDER"
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
