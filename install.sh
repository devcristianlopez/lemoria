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
echo "  OK"

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
python3 -m pip install --user -q -e "$LEMORIA_DIR[dev]" 2>/dev/null || python3 -m pip install -q -e "$LEMORIA_DIR[dev]"
echo "  Dependencias instaladas"

# Asegurar que ~/.local/bin esté en PATH para el usuario
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

# ----- opencode.jsonc -----
echo "[6/7] Configurando OpenCode..."
if command -v opencode >/dev/null 2>&1; then
    echo "  OpenCode detectado"
    echo "  Agentes disponibles en agents/"
else
    echo "  OpenCode no detectado, instalación opcional"
fi

# ----- Resumen -----
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
echo "  Para abrir Obsidian vault:"
echo "    obsidian $LEMORIA_DIR/vault/obsidian/"
echo ""
echo "  Para detener PostgreSQL:"
echo "    docker compose down"
echo ""
