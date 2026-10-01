#!/usr/bin/env bash
# Lógica del instalador, separada de install.sh para poder testearla.
#
# install.sh es un script lineal que hace prompts, lee de stdin, escribe en
# $HOME y arranca contenedores: no se puede ejecutar en un test. Acá viven solo
# las decisiones —qué base usar, qué instalador probar, cómo decirle a cada
# distro qué paquete instalar— que son justamente las partes donde un error
# produce un mensaje falso o un crash. Este archivo no hace nada al ser sourced:
# solo define funciones. install.sh lo carga y sigue como antes.
#
# Los tests (tests/test_installer.py) corren estas mismas funciones en un
# subshell con un PATH falso, así que lo que se prueba acá es exactamente lo que
# corre en la máquina del usuario.

# Los tres proveedores posibles de la base.
DB_PROVIDER_PREEXISTING="preexistente"
DB_PROVIDER_DOCKER="docker"
DB_PROVIDER_NONE="ninguno"

# ----- Detección del entorno -----

# El puerto que va a escuchar la base. Sale del entorno para poder correr el
# instalador contra un Postgres de pruebas sin editar .env.
resolve_db_port() {
    printf '%s' "${LEMORIA_DB_PORT:-5432}"
}

# PostgreSQL: Docker ya no es obligatorio. What matters is whether something
# answers on the TCP port the app connects to -- pg_isready with no host only
# checks the Unix socket, which says nothing about a container or a server
# listening on TCP alone.
# Deja el resultado en PG_READY (string "true"/"false", como lo espera el
# `if $PG_READY` de install.sh).
detect_postgres() {
    PG_READY=false
    if command -v pg_isready >/dev/null 2>&1 &&
        pg_isready -h localhost -p "$DB_PORT" -q 2>/dev/null; then
        PG_READY=true
    fi
}

# Docker tiene dos formas distintas de fallar, así que lleva dos flags.
# DOCKER_BINARIO dice "el ejecutable existe"; DOCKER_USABLE dice "el daemon
# contesta". Son estados distintos y el usuario tiene que poder ver cuál falló.
#
# Probar 'docker compose version' NO sirve para lo segundo: eso solo lee la
# versión del plugin CLI y nunca toca el socket, así que sale con 0 incluso
# cuando el daemon es inaccesible. Ahí el script avanzaba hasta
# 'docker compose up -d' y moría con "permission denied" bajo `set -e`.
# 'docker info' sí conversa con el daemon, y por lo tanto falla cuando tiene
# que fallar.
detect_docker() {
    DOCKER_BINARIO=false
    if command -v docker >/dev/null 2>&1; then
        DOCKER_BINARIO=true
    fi
    DOCKER_USABLE=false
    if $DOCKER_BINARIO && docker info >/dev/null 2>&1; then
        DOCKER_USABLE=true
    fi
}

# ----- La base de datos -----

# Decide de dónde sale la base SIN arrancar nada: install.sh después hace lo que
# corresponda. La regla es que algo ya andando gana siempre, porque el
# instalador no administra servidores que ya estaban corriendo.
resolve_db_provider() {
    if $PG_READY; then
        printf '%s' "$DB_PROVIDER_PREEXISTING"
    elif $DOCKER_USABLE; then
        printf '%s' "$DB_PROVIDER_DOCKER"
    else
        printf '%s' "$DB_PROVIDER_NONE"
    fi
}

# Verifica las credenciales de .env contra el servidor que ya estaba corriendo.
# El resultado va en PG_CREDENTIALS ("ok" | "no-psql" | "invalid") para que quien
# llama pueda decidir sin parsear el texto impreso.
verify_preexisting_postgres() {
    local port="$1" user="$2" password="$3" dbname="$4"
    PG_CREDENTIALS="no-psql"
    if ! command -v psql >/dev/null 2>&1; then
        echo "  PostgreSQL responde en localhost:$port y no se tocó."
        echo "  No encontré 'psql', así que no pude verificar las credenciales."
        echo "  Si Lemoria falla al conectar, revisá LEMORIA_DB_* en .env."
        return 0
    fi
    if PGPASSWORD="$password" psql \
        -h localhost -p "$port" \
        -U "$user" -d "$dbname" \
        -tAc "SELECT 1" >/dev/null 2>&1; then
        PG_CREDENTIALS="ok"
        echo "  PostgreSQL ya responde en localhost:$port — no se tocó"
        echo "  Credenciales de .env válidas ($user@localhost/$dbname)"
    else
        PG_CREDENTIALS="invalid"
        echo "  ! PostgreSQL responde en localhost:$port pero las credenciales"
        echo "    de .env no sirven. Ajusta LEMORIA_DB_* y reintenta, o crea la"
        echo "    base a mano. El instalador no administra este servidor."
    fi
}

# Levanta el stack de Docker y espera a que la base quede aceptando conexiones.
# Devuelve 1 con un mensaje en vez de dejar que `set -e` aborte en silencio.
start_docker_postgres() {
    local port="$1"
    # DOCKER_USABLE ya se validó antes, pero el daemon puede caer entre esa
    # comprobación y acá. Sin este guard, `set -e` convierte el fallo en un
    # error sin contexto y el usuario no sabe qué hacer.
    if ! docker compose up -d; then
        echo ""
        echo "  ERROR: 'docker compose up -d' falló. El daemon responde pero el"
        echo "  stack no levantó. Causas frecuentes:"
        echo "    • otro servicio ya ocupa el puerto $port"
        echo "    • falta la imagen o el build falló (mirá la salida de arriba)"
        echo "  Sin Docker, la alternativa es más simple:"
        echo "    $(pkg_hint postgresql postgresql) && sudo systemctl enable --now postgresql"
        return 1
    fi
    echo "  Esperando que PostgreSQL esté saludable..."
    # El until sin límite cuelga el instalador para siempre si el contenedor
    # arranca pero nunca queda aceptando conexiones. 60 intentos y se declara
    # el fallo, que es información útil; un colgado silencioso no lo es.
    local HEALTHY=false
    local _
    for _ in $(seq 1 60); do
        if docker compose exec db pg_isready -U lemoria >/dev/null 2>&1; then
            HEALTHY=true
            break
        fi
        sleep 1
    done
    if ! $HEALTHY; then
        echo "  ERROR: el contenedor arrancó pero PostgreSQL no quedó listo en"
        echo "  60 segundos. Logs:  docker compose logs db"
        return 1
    fi
    echo "  PostgreSQL (Docker) listo"
}

# Punto de entrada de la sección "[3/9] Configurando PostgreSQL": deja la base
# andando y dice en DB_PROVIDER de dónde salió, para que el resumen final no
# tenga que adivinarlo.
provide_postgres() {
    local port="$1" user="$2" password="$3" dbname="$4"
    DB_PROVIDER="$(resolve_db_provider)"
    case "$DB_PROVIDER" in
        "$DB_PROVIDER_PREEXISTING")
            # Algo ya responde en el puerto y no es asunto nuestro. El
            # instalador no administra servidores que ya estaban corriendo:
            # solo verifica que las credenciales de .env sirvan, y avisa con
            # precisión si no.
            verify_preexisting_postgres "$port" "$user" "$password" "$dbname"
            ;;
        "$DB_PROVIDER_DOCKER")
            start_docker_postgres "$port"
            ;;
        *)
            # install.sh ya abortó antes de llegar acá con la guía de
            # instalación; si alguien llama a esta función directo, que devuelva
            # error en vez de seguir como si tuviera una base.
            return 1
            ;;
    esac
}

# Cómo detener PostgreSQL depende de quién lo levantó. Decir 'docker compose
# down' sin más era información falsa: a un usuario con PostgreSQL nativo eso
# lo mandaba a un error y lo dejaba creyendo que había algo roto.
#
# Cada valor que resolve_db_provider puede emitir tiene SU rama, y se comparan
# contra las variables DB_PROVIDER_* de arriba, nunca contra un literal. Un
# provider escrito a mano en dos lugares diverge en silencio: el `case` deja de
# coincidir, cae en '*' y el usuario lee "no quedó levantado por este
# instalador" sobre un PostgreSQL que llevaba andando todo el rato.
print_db_stop_hint() {
    case "$1" in
        "$DB_PROVIDER_PREEXISTING")
            echo "  PostgreSQL ya estaba corriendo en localhost:$DB_PORT — no se tocó."
            echo "  Para detenerlo:"
            if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q postgresql; then
                echo "    sudo systemctl stop postgresql"
            else
                # Sin unidad systemd no es un servicio del sistema: alguien lo
                # levantó de otra forma (contenedor, gestor de servicios, a mano).
                echo "    No encontré una unidad systemd de postgresql, así que este"
                echo "    servidor no lo maneja systemd. Si lo levantaste con Docker:"
                echo "      docker compose down"
                echo "    Si no, detenelo con lo que usaste para arrancarlo."
            fi
            ;;
        "$DB_PROVIDER_DOCKER")
            echo "  PostgreSQL levantado por este instalador con Docker Compose."
            echo "  Para detenerlo:"
            echo "    docker compose down"
            echo "    docker compose down -v     # borra también el volumen de datos"
            ;;
        "$DB_PROVIDER_NONE")
            # Sin base no hay nada que este instalador haya dejado andando, así
            # que tampoco hay nada que detener. install.sh aborta antes de llegar
            # acá con la guía de instalación.
            echo "  No se eligió ninguna base: este instalador no levantó PostgreSQL."
            echo "  Si tenés una corriendo por tu cuenta, no se tocó."
            ;;
        *)
            # Solo alcanzable si alguien llama a esta función con un valor que
            # resolve_db_provider no emite. Decir cuál recibió hace el bug
            # visible en vez de dejar un mensaje que parece de un caso real.
            echo "  Proveedor de base desconocido ('$1'): no hay instrucciones para detener."
            ;;
    esac
}



# ----- OpenCode TUI plugin -----

install_opencode_lemoria_menu() {
    local repo_dir="$1" opencode_dir="$2" agents_dir="${3:-$opencode_dir/agents}"
    local source_dir="$repo_dir/opencode/plugins/lemoria-menu"
    local target_dir="$opencode_dir/plugins/lemoria-menu"
    local cli_json="$opencode_dir/cli.json"

    if [ ! -f "$source_dir/tui.js" ]; then
        echo "  ! Plugin Lemoria menu no encontrado en $source_dir"
        return 1
    fi

    mkdir -p "$target_dir"
    cp "$source_dir/tui.js" "$target_dir/tui.js"

    # El plugin necesita saber dónde vive el repo de Lemoria y en qué
    # directorio están los .md de los agentes, para escribir el pin del modelo
    # en el sitio correcto sin ensuciar el repositorio del usuario.
    LEMORIA_REPO="$repo_dir" AGENTS_DIR="$agents_dir" TARGET_DIR="$target_dir" python3 - <<'PYCFG'
import json
import os
from pathlib import Path

target = Path(os.environ["TARGET_DIR"])
target.mkdir(parents=True, exist_ok=True)
(target / "config.json").write_text(
    json.dumps(
        {"repo": os.environ["LEMORIA_REPO"], "agentsDir": os.environ["AGENTS_DIR"]},
        indent=2,
    )
    + "\n"
)

PYCFG

    CLI_JSON="$cli_json" PLUGIN_PATH="$target_dir" python3 - <<'PYCFG'
import json
import os
from pathlib import Path

path = Path(os.environ["CLI_JSON"])
plugin = os.environ["PLUGIN_PATH"]
path.parent.mkdir(parents=True, exist_ok=True)

if path.exists():
    try:
        data = json.loads(path.read_text() or "{}")
    except json.JSONDecodeError:
        path.with_suffix(path.suffix + ".bak").write_text(path.read_text())
        data = {}
else:
    data = {"$schema": "https://opencode.ai/v2/cli.json"}

plugins = data.get("plugins")
if not isinstance(plugins, list):
    plugins = []

# Idempotente: conserva los plugins que ya tenía el usuario.
plugins = [entry for entry in plugins if entry != plugin]
plugins.append(plugin)
data["plugins"] = plugins
path.write_text(json.dumps(data, indent=2) + "\n")
PYCFG
}

# ----- Mensajes de instalación -----

# Explicar cómo conseguir PostgreSQL cuando no hay ninguno escuchando. Vive
# como función porque dos caminos la necesitan (requisitos y resumen final) y
# la advertencia del grupo `docker` no puede quedar escrita dos veces y terminar
# divergiendo.
print_postgres_setup_guide() {
    echo ""
    echo "  Lemoria necesita PostgreSQL y nada responde en localhost:${DB_PORT}."
    echo "  Hay dos vías. La primera es la recomendada."
    echo ""
    echo "  A) PostgreSQL nativo (recomendado)"
    echo ""
    if command -v pacman >/dev/null 2>&1; then
        echo "     Arch / Omarchy:"
        echo "       sudo pacman -S postgresql"
        echo "       sudo systemctl enable --now postgresql"
    elif command -v apt-get >/dev/null 2>&1; then
        echo "     Debian / Ubuntu:"
        echo "       sudo apt install postgresql"
        echo "       sudo systemctl enable --now postgresql"
    elif command -v dnf >/dev/null 2>&1; then
        echo "     Fedora:"
        echo "       sudo dnf install postgresql"
        echo "       sudo systemctl enable --now postgresql"
    elif command -v brew >/dev/null 2>&1; then
        echo "     macOS:"
        echo "       brew install postgresql"
        echo "       brew services start postgresql"
    else
        echo "     No reconocí tu distribución. Instalá el paquete postgresql y"
        echo "     dejalo escuchando en el puerto ${DB_PORT}."
    fi
    echo ""
    echo "     Después creá el usuario y la base que Lemoria espera:"
    echo "       sudo -u postgres psql -c \"CREATE USER lemoria WITH PASSWORD 'lemoria';\""
    echo "       sudo -u postgres createdb -O lemoria lemoria"
    echo ""
    echo "  B) Docker (alternativa secundaria)"
    echo ""
    if $DOCKER_BINARIO; then
        # "Tengo el comando" y "tengo el daemon" son estados distintos, y el
        # segundo es el que revienta más abajo. Decirlo evita que el usuario
        # reinstale Docker sin notar que ya lo tenía.
        echo "     Tenés el binario 'docker' pero su daemon NO responde, así que"
        echo "     este script no puede usarlo. El estado real se ve con:"
        echo "       docker info"
        echo "     El error típico es el socket sin permisos: el daemon corre, pero"
        echo "     tu usuario no puede abrir /var/run/docker.sock."
        echo ""
    else
        echo "     Instalá Docker primero:"
        echo "       sudo pacman -S docker docker-compose"
        echo "       sudo systemctl enable --now docker"
        echo ""
    fi
    # El grupo docker concede por diseño lo mismo que root: acceso al socket del
    # daemon, que a su vez permite montar /, editar /etc/shadow y correr
    # contenedores privilegiados. Recomendarlo sin más esconde ese costo, así
    # que la advertencia va pegada al comando, no en un aparte.
    echo "     AVISO — sobre 'sudo usermod -aG docker \$USER':"
    echo "       El grupo docker es equivalente a root SIN contraseña. Todo lo que"
    echo "       quede en él escala a root de inmediato, sin que le pida la clave"
    echo "       a nadie. Lemoria NO lo recomienda: usá la vía A, que no pide ese"
    echo "       privilegio. Si aun así lo hacés, es porque aceptaste el riesgo:"
    echo "         sudo usermod -aG docker \$USER"
    echo "         newgrp docker   # en ESA MISMA terminal, antes de reintentar ./install.sh"
    echo "       # alternativa: cerrá sesión y volvé a entrar"
    echo ""
    echo "  Después de 'newgrp docker' (o de reiniciar sesión), volvé a correr ./install.sh"
    echo "  cuando algo responda en localhost:${DB_PORT}."
}

# Nombres de paquete para el mismo requisito según la familia de distribución.
# Un comando equivocado en el mensaje de error es peor que no decir nada: en
# Arch el paquete se llama `python-pipx`, no `pipx`, y el módulo venv viene en
# `python`, no en `python3-venv`. Decir "sudo apt install" a un usuario de Arch
# lo manda a un binario que no existe, y el mensaje pasa a ser el problema.
pkg_hint() {
    if command -v pacman >/dev/null 2>&1; then
        printf 'sudo pacman -S %s' "$1"
    elif command -v apt-get >/dev/null 2>&1; then
        printf 'sudo apt install %s' "$2"
    else
        printf 'instalá "%s" (o "%s") con el gestor de paquetes de tu sistema' "$1" "$2"
    fi
}

# uv es el único caso con historia distinta: en Arch es un paquete normal, pero
# fuera de los repos oficiales se instala desde su propia documentación, así que
# no hay un nombre de paquete universal que sobreescribir.
uv_install_hint() {
    if command -v pacman >/dev/null 2>&1; then
        printf 'sudo pacman -S uv'
    else
        printf 'uv no viene en los repos de tu distro; instrucciones en https://docs.astral.sh/uv/getting-started/installation/'
    fi
}

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

# ----- Instalación de Lemoria como comando global -----

install_with_uv() {
    # --editable deja este checkout como fuente de verdad: los cambios en el
    # código se reflejan sin reinstalar, que es lo mismo que hacía el -e de pip.
    # El extra [dev] se escribe como path[extra] (PEP 508) y es lo que trae
    # pytest y ruff; verificado contra uv 0.12.x.
    echo "  uv tool install --editable \"$LEMORIA_DIR[dev]\""
    uv tool install --editable "$LEMORIA_DIR[dev]"
}

install_with_venv() {
    local VENV_DIR="$HOME/.local/share/lemoria/venv"
    echo "  Creando venv en $VENV_DIR ..."
    if ! python3 -m venv "$VENV_DIR"; then
        echo "  ! no se pudo crear el venv"
        return 1
    fi
    echo "  Instalando dependencias en el venv..."
    if ! "$VENV_DIR/bin/pip" install -q -e "$LEMORIA_DIR[dev]"; then
        echo "  ! falló la instalación dentro del venv"
        return 1
    fi
    mkdir -p "$HOME/.local/bin"
    ln -sf "$VENV_DIR/bin/lemoria" "$HOME/.local/bin/lemoria"
    echo "  ✓ comando disponible en ~/.local/bin/lemoria"
}

install_with_pip() {
    # Sin 2>/dev/null a propósito. Tapar el error hace que un pip que falló
    # por PEP 668 sea indistinguible de uno que funcionó, y cuando la cadena
    # entera se cae el usuario no tiene ni el motivo ni la pista de qué
    # instalar. El error va a la consola, que es donde lo está mirando.
    python3 -m pip install --user -q -e "$LEMORIA_DIR[dev]" || \
    python3 -m pip install -q -e "$LEMORIA_DIR[dev]"
}

# Camino 1: uv. Es el primario porque resuelve dependencias y crea el
# aislamiento él solo, sin tocar el intérprete del sistema ni pedir sudo.
#
# Los tres caminos se reciben como parámetros para que los tests puedan poner
# dobles y comprobar cuál se elige. install.sh los llama sin argumentos y
# recibe los de verdad, así que lo que decide esta función es exactamente lo
# que corre el instalador.
choose_installer() {
    local uv_fn="${1:-install_with_uv}"
    local venv_fn="${2:-install_with_venv}"
    local pip_fn="${3:-install_with_pip}"
    local UV_AVAILABLE=false

    if command -v uv >/dev/null 2>&1; then
        UV_AVAILABLE=true
    fi

    # Caminos 2 y 3: venv y pip. El orden va de más limpio a más invasivo, así que
    # el último es el que más puede romperle el sistema al usuario — por eso es
    # también el que menos se explica.
    INSTALLER=""

    if $UV_AVAILABLE; then
        echo "  → uv (primario, $(uv --version 2>/dev/null || echo 'disponible'))"
        if "$uv_fn"; then
            INSTALLER="uv"
            # uv deja el ejecutable en su propio directorio de binarios, que por
            # defecto es ~/.local/bin pero se puede mover con UV_TOOL_BIN_DIR. Sin
            # esto, una instalación por uv que sale con 0 igual terminaba en
            # "comando no encontrado" más abajo.
            UV_BIN_DIR="$(uv tool dir --bin 2>/dev/null || true)"
        else
            echo "  ! uv no pudo instalar Lemoria, pruebo con venv propio"
        fi
    else
        echo "  → uv no está instalado, arranco por venv propio"
    fi

    if [ -z "$INSTALLER" ]; then
        echo "  → venv propio"
        if "$venv_fn"; then
            INSTALLER="venv"
        fi
    fi

    if [ -z "$INSTALLER" ]; then
        echo "  → pip del sistema (último recurso)"
        if "$pip_fn"; then
            INSTALLER="pip"
        fi
    fi

    [ -n "$INSTALLER" ]
}
