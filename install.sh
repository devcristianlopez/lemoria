#!/usr/bin/env bash
set -euo pipefail

LEMORIA_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$LEMORIA_DIR"

echo "========================================"
echo "  Lemoria — Instalación automatizada"
echo "========================================"
echo ""

# ----- Verificar requisitos -----
echo "[1/6] Verificando requisitos..."

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 no encontrado"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker no encontrado"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: docker compose no encontrado"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git no encontrado"; exit 1; }

echo "  python3 : $(python3 --version)"
echo "  docker  : $(docker --version)"
echo "  git     : $(git --version)"
echo "  OK"

# ----- .env -----
echo "[2/6] Configurando .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  .env creado desde .env.example"
else
    echo "  .env ya existe, se mantiene"
fi

# ----- Docker Compose -----
echo "[3/6] Iniciando PostgreSQL (Docker)..."
docker compose up -d
echo "  Esperando que PostgreSQL esté saludable..."
until docker compose exec db pg_isready -U lemoria >/dev/null 2>&1; do
    sleep 1
done
echo "  PostgreSQL listo"

# ----- Python venv -----
echo "[4/6] Instalando dependencias Python..."
if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo "  Virtual env creado en .venv/"
fi
source .venv/bin/activate
pip install -q -e ".[dev]"
echo "  Dependencias instaladas"

# ----- Inicializar -----
echo "[5/6] Inicializando Lemoria..."
python -m lemoria init
echo "  Base de datos inicializada"
echo "  Vault listo en vault/obsidian/"

# ----- Resumen -----
echo "[6/6] Instalación completada"
echo ""
echo "========================================"
echo "  Lemoria está listo"
echo "========================================"
echo ""
echo "  Para activar el entorno:"
echo "    source .venv/bin/activate"
echo ""
echo "  Comandos útiles:"
echo "    python -m lemoria project create \"mi-proyecto\""
echo "    python -m lemoria agent list"
echo "    python -m lemoria --help"
echo ""
echo "  Para abrir Obsidian vault:"
echo "    obsidian vault/obsidian/"
echo ""
echo "  Para detener PostgreSQL:"
echo "    docker compose down"
echo ""
