#!/usr/bin/env bash
set -euo pipefail

LEMORIA_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$LEMORIA_DIR"

echo "========================================"
echo "  Lemoria — Instalación automatizada"
echo "========================================"
echo ""

# ----- Verificar requisitos -----
echo "[1/7] Verificando requisitos..."

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 no encontrado"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker no encontrado"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: docker compose no encontrado"; exit 1; }

echo "  python3 : $(python3 --version)"
echo "  docker  : $(docker --version)"

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
echo "[2/7] Configurando .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  .env creado desde .env.example"
else
    echo "  .env ya existe, se mantiene"
fi

# ----- Docker Compose -----
echo "[3/7] Iniciando PostgreSQL (Docker)..."
docker compose up -d
echo "  Esperando que PostgreSQL esté saludable..."
until docker compose exec db pg_isready -U lemoria >/dev/null 2>&1; do
    sleep 1
done
echo "  PostgreSQL listo"

# ----- Instalar Lemoria como comando global -----
echo "[4/7] Instalando Lemoria como comando global..."

install_with_pip() {
    python3 -m pip install --user -q -e "$LEMORIA_DIR[dev]" 2>/dev/null || \
    python3 -m pip install -q -e "$LEMORIA_DIR[dev]" 2>/dev/null
}

install_with_venv() {
    local VENV_DIR="$HOME/.local/share/lemoria/venv"
    python3 -m venv "$VENV_DIR" 2>/dev/null || python3 -m venv --without-pip "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -q -e "$LEMORIA_DIR[dev]" 2>/dev/null || \
        "$VENV_DIR/bin/pip3" install -q -e "$LEMORIA_DIR[dev]"
    mkdir -p "$HOME/.local/bin"
    ln -sf "$VENV_DIR/bin/lemoria" "$HOME/.local/bin/lemoria"
    echo "  Instalado en venv propio: $VENV_DIR"
}

if install_with_pip; then
    echo "  Dependencias instaladas (pip)"
else
    echo "  pip system-wide no disponible (PEP 668), usando venv propio..."
    install_with_venv
    echo "  Dependencias instaladas (venv)"
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
echo "[5/7] Inicializando Lemoria..."
lemoria init
echo "  Base de datos inicializada"
echo "  Vault listo en vault/obsidian/"

# ----- Configurar OpenCode -----
OPENCODE_GLOBAL_DIR="$HOME/.config/opencode"

if [ "$INSTALL_MODE" = "1" ]; then
    echo "[6/7] Instalando agentes en modo GLOBAL..."

    mkdir -p "$OPENCODE_GLOBAL_DIR/agents"
    mkdir -p "$OPENCODE_GLOBAL_DIR/skills/lemoria"

    cp .opencode/agents/*.md "$OPENCODE_GLOBAL_DIR/agents/"
    cp .opencode/skills/lemoria/SKILL.md "$OPENCODE_GLOBAL_DIR/skills/lemoria/"
    echo "  Agentes copiados a $OPENCODE_GLOBAL_DIR/agents/"

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
    echo "[6/7] Instalación en modo PROYECTO..."
    echo "  Agentes locales en .opencode/agents/"
    echo "  Abre OpenCode desde esta carpeta para usarlos"
fi

# ----- Resumen -----
echo ""
echo "[7/7] Instalación completada"
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
echo "    @orchestrator, @backend-agent, @testing-agent, ..."
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
echo "  Para abrir Obsidian vault:"
    echo "    obsidian $LEMORIA_DIR/vault/obsidian/"
    echo ""
    echo "  Para detener PostgreSQL:"
    echo "    docker compose down"
echo ""
