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
              • PostgreSQL (el que ya tengas, o Docker)
                        ↓
┌──────────────────────────────────────────────────┐
│  ~/mi-proyecto/ (carpeta vacía para tu código)   │
│  Abres OpenCode aquí y los agentes globales      │
│  están disponibles automáticamente.              │
└──────────────────────────────────────────────────┘
```

## Requisitos

- **Python** >= 3.11
- **[uv](https://docs.astral.sh/uv/)** — recomendado. Es el primer camino que
  prueba el instalador y el único que no necesita ni `sudo` ni tocar el
  intérprete del sistema. En Arch/Omarchy: `sudo pacman -S uv`
- **PostgreSQL** >= 14 — nativo del sistema o Docker, el que ya tengas
- **OpenCode** (CLI)
- **Obsidian** (opcional)
- **GitHub CLI `gh`** (opcional, para PRs automáticos)

**`pip` no es un requisito.** En Arch el intérprete del sistema no trae `pip`
y además está protegido por PEP 668, así que `pip install` contra él falla
siempre. Está igual como último recurso, pero no es el camino esperado: los
detalles están en [Por qué `pip install` falla en Arch con Python 3.14](#por-qué-pip-install-falla-en-arch-con-python-314).

Docker **tampoco** es obligatorio. Si ya tenés un PostgreSQL corriendo (en Arch
es lo normal), el instalador lo detecta y lo deja como está: no administra
servidores que ya estaban andando. Si no hay ninguno, te guía para elegir
entre nativo y Docker — con nativo como opción recomendada.

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
| 1 | Verifica Python y cómo llega a PostgreSQL (nativo, Docker, o ninguno) |
| 2 | Crea `.env` |
| 3 | Verifica las credenciales contra el PostgreSQL que ya responde, o lo levanta con Docker si no hay ninguno. Si no hay ninguna de las dos, se detiene con la guía de instalación |
| 4 | Instala `lemoria` como comando global (`uv` → venv propio → `pip`) |
| 5 | Inicializa la base de datos |
| 6 | Copia agentes y skills a `~/.config/opencode/`, con `default_agent: orchestrator` |
| 7 | Configura Context7 MCP (documentación en tiempo real para librerías) |
| 8 | Detecta tu entorno: registra los agentes, ofrece el panel de Omarchy y avisa si no hay opencode |
| 9 | Resumen con lo que quedó instalado |

El paso 8 es el que decide las integraciones según la máquina: el panel de
Omarchy solo se ofrece si estás en Omarchy, y la telemetría solo se activa si
existe un `opencode.db`. Ninguna de las dos es obligatoria para instalar Lemoria.

### Paso 3 en detalle: PostgreSQL nativo antes que Docker

El instalador no administra servidores que ya estaban corriendo. La regla es
una sola y siempre gana lo que ya anda:

| Estado en `localhost:5432` | Qué hace |
|---|---|
| Algo responde | Lo respeta. No lo toca. Verifica que las credenciales de `.env` sirvan y avisa si no |
| Nada responde, Docker usable | Levanta el stack con `docker compose up -d` y espera a que la base esté sana |
| Nada responde, Docker no usable | **Se detiene** y te muestra las dos vías de instalación, con la nativa recomendada |

El puerto no es fijo: sale de `LEMORIA_DB_PORT` en `.env` (por defecto `5432`).

El probe es `pg_isready -h localhost -p <puerto>`, con host explícito a
propósito. `pg_isready` sin `-h` solo mira el socket Unix, así que un
PostgreSQL que escucha únicamente en TCP —un contenedor, un servidor con
`listen_addresses`— aparecería como ausente y el instalador intentaría levantar
otro sobre un puerto ya ocupado.

Si usaste Docker, el instalador espera a que la base esté sana con un tope de
**60 segundos**. Si el contenedor arrancó pero nunca acepta conexiones, falla
con un mensaje y te dice dónde mirar los logs, en vez de quedarse colgado.

Al final, el resumen te dice cómo **detener** la base según quién la levantó:
`docker compose down` si la levantó el instalador, `sudo systemctl stop
postgresql` si ya venía andando, y un aviso explícito si algo ya estaba corriendo
pero systemd no lo administra —porque en ese caso `docker compose down` sería
información falsa.

### Paso 4 en detalle: `uv` → venv → `pip`

El instalador prueba tres caminos, en orden de menos a más invasivo:

| # | Camino | Comando | Cuándo |
|---|--------|---------|--------|
| 1 | **uv** (recomendado) | `uv tool install --editable "<repo>[dev]"` | Siempre que `uv` esté instalado |
| 2 | **venv propio** | `python3 -m venv ~/.local/share/lemoria/venv` + `pip install -e "<repo>[dev]"` + symlink a `~/.local/bin/lemoria` | Si no tenés `uv`, o si `uv` falla |
| 3 | **pip del sistema** | `python3 -m pip install --user -e "<repo>[dev]"`, y sin `--user` si el anterior falla | Último recurso |

`uv` va primero porque resuelve dependencias y crea el aislamiento él solo: no
toca el intérprete del sistema, no pide `sudo` y no depende de que el
distribuidor empaquete `pip`. El `[dev]` es un extra PEP 508 escrito como
`path[extra]`, y es lo que trae `pytest` y `ruff`.

El orden importa: el camino 3 es el único que puede romperle el sistema al
usuario, y por eso es el que menos se explica. Si los tres fallan, el mensaje
final los lista con el comando exacto de cada uno.

`--editable` deja este checkout como fuente de verdad: los cambios en el código
se reflejan sin reinstalar.

El error de `pip` **no** se tapa con `2>/dev/null`. Si falla, el motivo se ve
en pantalla — que es exactamente lo que hace falta cuando lo que falla es PEP
668.

### Docker: dos estados, no uno

El instalador distingue dos cosas que antes iban mezcladas:

| Flag | Significado |
|---|---|
| `DOCKER_BINARIO` | El ejecutable `docker` existe |
| `DOCKER_USABLE` | El daemon responde (`docker info`) |

Son estados distintos y el usuario tiene que poder ver cuál falló. Tener el
comando instalado y poder usarlo son dos cosas diferentes, y confundirlas hace
que alguien reinstale Docker sin notar que ya lo tenía.

El probe es **`docker info`**, y no `docker compose version` como antes. Este
último solo lee la versión del plugin de CLI y nunca toca el socket, así que
sale con `exit 0` incluso cuando el daemon es inaccesible. Con ese probe, el
script avanzaba hasta `docker compose up -d` y moría con `permission denied`
sin contexto. `docker info` sí conversa con el daemon, y por lo tanto falla
cuando tiene que fallar.

Si tenés el binario pero el daemon no responde, el instalador **no crashea**:
te dice qué pasó, que el estado real se ve con `docker info`, y cuál es el
error típico (el socket `/var/run/docker.sock` sin permisos para tu usuario).

### Después de instalar

```bash
# Verifica que lemoria funciona (desde cualquier directorio)
lemoria --version
lemoria --help

# Los agentes quedaron registrados
lemoria agent list

# Consumo de opencode (si ya lo usaste)
lemoria usage

# El repo lemoria/ ya no hace falta, puedes borrarlo:
# rm -rf ~/lemoria
```

> Si borraste el repo, `lemoria agent sync` y `agent model` van a seguir
> funcionando: leen y escriben los `.md` de donde estén, y el modo global los
> deja en `~/.config/opencode/agents/`.

## Por qué `pip install` falla en Arch con Python 3.14

Si llegaste hasta acá, casi seguro viste uno de estos:

```
/usr/bin/python3: No module named pip
```

o

```
error: externally-managed-environment
```

Son **dos** problemas distintos de Arch, y ninguno es culpa de Lemoria:

**1. En Arch, `pip` no viene con Python.** Es un paquete aparte:

```bash
sudo pacman -S python-pip     # NO es "sudo pacman -S pip"
```

Sin ese paquete, `python3 -m pip` responde `No module named pip` aunque tengas
`pip` instalado por otro lado (un venv, `uv`, pipx). El comando existe en el
venv y no existe en el intérprete del sistema: son dos entornos distintos.

**2. El intérprete del sistema está protegido por PEP 668.** Arch lo marca con
`/usr/lib/python3.14/EXTERNALLY-MANAGED`, y por eso cualquier `pip install`
contra `/usr/bin/python3` se rechaza. La protección existe por una razón: en
Arch los paquetes de Python se gestionan con `pacman`, y meter uno a mano
desincroniza tu sistema de los repos y rompe el próximo `pacman -Syu`.

`--break-system-packages` desactiva esa protección, y por eso el instalador lo
ofrece solo como último recurso, avisando que puede romper otras herramientas.
En una notebook que es tu máquina de trabajo, no es el camino recomendado.

**Y si pensabas en pipx:** el paquete en Arch se llama `python-pipx`, **no**
`pipx` (ese nombre es de Debian/Ubuntu). `pipx` tampoco está en el camino del
instalador porque `uv` cumple el mismo papel con menos piezas.

### Resumen: qué instalar según tu distro

| Si sos de… | Instalá esto | Evitá esto |
|---|---|---|
| Arch / Omarchy | `sudo pacman -S uv` | `pip install` contra el intérprete del sistema |
| Debian / Ubuntu | `sudo apt install python3-venv` | lo mismo |
| Cualquier otra | [instrucciones de uv](https://docs.astral.sh/uv/getting-started/installation/) | lo mismo |

## Sobre `sudo usermod -aG docker $USER`

Si llegaste a este punto es porque elegiste Docker como vía para PostgreSQL y
el daemon no responde. Es tentador copiar este comando de un tutorial. No lo
hagas sin leer esto.

> **El grupo `docker` es equivalente a root, sin contraseña.**
>
> Quien esté en el grupo `docker` tiene acceso al socket del daemon, y desde
> ahí tiene lo mismo que root: montar `/` dentro de un contenedor, editar
> `/etc/shadow`, correr contenedores privilegiados. **No pide la clave de
> nadie en ningún momento.** No es un permiso "parecido a root": es root.
>
> El riesgo no es teórico. Cualquier proceso que logree ejecutarse como tu
> usuario —un script que descargaste, una dependencia npm sospechosa, un
> repositorio que clonaste para leerlo— escala a root de inmediato.

Por eso Lemoria **no lo recomienda**, y la razón está en el propio instalador:
la vía A (PostgreSQL nativo) no pide ese privilegio en absoluto. Antes de
sumarte al grupo, preguntate si realmente necesitás Docker o si con
`sudo pacman -S postgresql` ya resolvés lo que estabas intentando hacer.

Si aun así lo hacés, es porque aceptaste el riesgo:

```bash
sudo usermod -aG docker $USER
newgrp docker          # o cerrá sesión y volvé a entrar
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

Reproduce exactamente lo que hace `install.sh`, en el mismo orden de decisión.
Cada paso indica qué alternativa tomaría el instalador.

```bash
# 1. Clonar
git clone https://github.com/devcristianlopez/lemoria.git
cd lemoria

# 2. Configurar
cp .env.example .env

# 3. PostgreSQL — NATIVO primero (recomendado en Arch / Omarchy)
sudo pacman -S postgresql
sudo systemctl enable --now postgresql
sudo -u postgres psql -c "CREATE USER lemoria WITH PASSWORD 'lemoria';"
sudo -u postgres createdb -O lemoria lemoria

#    ...o DOCKER, solo si preferís la base aislada.
#    Antes de sumarte al grupo docker, leé la advertencia de arriba.
# docker compose up -d

# 4. Instalar el comando global con uv (camino 1)
sudo pacman -S uv
uv tool install --editable ".[dev]"
export PATH="$PATH:$HOME/.local/bin"

#    Sin uv? El camino 2 crea su propio venv y publica el comando:
# python3 -m venv ~/.local/share/lemoria/venv
# ~/.local/share/lemoria/venv/bin/pip install -e ".[dev]"
# mkdir -p ~/.local/bin
# ln -sf ~/.local/share/lemoria/venv/bin/lemoria ~/.local/bin/lemoria

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
  "skills": ["~/.config/opencode/skills"]
}
EOF

# 8. Instalar Context7 MCP (documentación en tiempo real)
npx -y ctx7 setup --opencode --mcp

# 9. Listo. El repo lemoria/ ya no es necesario
cd ~
rm -rf lemoria  # opcional
```

No uses `pip install -e ".[dev]"` contra el intérprete del sistema como paso 4:
en Arch eso falla. El `pip` del venv de la línea 309 sí sirve, porque no es el
del sistema. Si elegiste nativo en el paso 3, no necesitás el `docker` de este
repo en ningún momento.

## Comandos básicos (funcionan desde cualquier lado)

```bash
lemoria project create "mi-api" -d "API REST"
lemoria project list
lemoria conv create <project-id> -t "Feature: login"
lemoria conv add <conv-id> user "descripción"
lemoria flow start <project-id> "sistema de auth"
lemoria flow list <project-id>
lemoria task create <project-id> <prd-id> -t "modelo User" -a implementation-agent
lemoria task list <project-id>
lemoria commit sync                         # reconstruye git → task desde trailers Task: <uuid>
lemoria commit list --project <project-id>  # sha, mensaje, autor y tarea enlazada
lemoria commit add <sha> --task <task-id>   # registra un commit puntual
lemoria decision log <project-id> -t "usar JWT" -d "stateless"
lemoria agent list
```

Para que un commit quede enlazado automáticamente, el mensaje debe incluir el
trailer que usa el github-agent:

```text
Task: <task-id>
```

`lemoria commit sync` es idempotente: lo puedes correr después de cada tanda o
para backfillear historial viejo sin duplicar filas.

## Panel propio de Omarchy (solo si usás Omarchy)

Si estás en Omarchy, Lemoria instala un plugin propio además del record JSON:

```bash
lemoria omarchy install --interval 1min  # plugin + record privado + timer de usuario, lo activa
lemoria budget 500M          # opcional: presupuesto mensual en tokens
lemoria omarchy record --print
lemoria omarchy where
```

Durante la instalación Lemoria intenta registrar el plugin en la barra con:

```bash
omarchy plugin enable lemoria.usage --after omarchy.agents
```

Si el comando no pudo ejecutarse automáticamente, corrélo a mano y recargá Omarchy.

No toca `/usr/share/omarchy`. El plugin se copia a
`~/.config/omarchy/plugins/lemoria.usage`, el record privado a
`~/.local/state/lemoria/omarchy/usage.json`, y el timer a
`~/.config/systemd/user/lemoria-usage.{service,timer}`. Se deshace con:

```bash
lemoria omarchy uninstall
```

El widget muestra el total histórico siempre en la barra. Al abrirlo ves hoy,
los últimos 7 días y la tabla de todos los agentes conocidos, incluso con cero
uso. En cada fila, `model` es el modelo de display actual/configurado/default;
el modelo inferido desde uso histórico aparece separado como `observedModel` / `obs ...`.
El presupuesto aparece solo si lo configurás. El timer también
sanea el bug intermitente de Codex cuando el collector nativo escribe
`account/read`. Los que no usan Omarchy tienen lo
mismo por CLI:

```bash
lemoria usage
lemoria usage --json
```

### Si el panel no se ve

El widget debería mostrar `0` incluso antes de que haya consumo, y al abrirlo
debería enseñar un estado vacío. Si no aparece ni ese `0`, revisá:

```bash
omarchy plugin enable lemoria.usage --after omarchy.agents
test -f ~/.config/omarchy/plugins/lemoria.usage/Panel.qml
lemoria omarchy where
test -f ~/.local/state/lemoria/omarchy/usage.json || lemoria omarchy record
systemctl --user status lemoria-usage.timer
systemctl --user list-timers lemoria-usage.timer --no-pager
```

Para cambios visuales del plugin ya instalado (márgenes, separación con
Bluetooth, tamaño del botón), ejecutá `omarchy restart shell` después de
actualizarlo. Un rescan de plugins puede detectar archivos nuevos sin reconstruir
la instancia visible de la barra.

El record sigue siendo Lemoria-owned: no debe aparecer como
`~/.local/state/omarchy/agents/usage/lemoria.json`. Si existe uno legado,
`lemoria omarchy install --interval 1min` lo borra y reinstala el plugin propio.

Si el panel deja de actualizar, el timer suele estar *activo pero sin disparo
programado*: `systemctl --user list-timers` muestra `-` en la columna NEXT
aunque diga `active`. Es el estado `elapsed`, y se arregla así:

```bash
systemctl --user stop lemoria-usage.timer
systemctl --user start lemoria-usage.service   # rearma el ancla del timer
systemctl --user start lemoria-usage.timer
```

`lemoria omarchy install` verifica eso al terminar y repara el timer si
encuentra el estado roto.

## Fijar el modelo de un agente (opcional)

Por defecto los agentes **heredan** el modelo de quien los invoca, y podés
cambiarlo cuando quieras:

```bash
lemoria agent model                                        # ver los modelos
lemoria agent model implementation-agent <modelo> -v high   # fijar modelo y effort
lemoria agent model implementation-agent --clear           # volver a heredar
```

## Notas

- **Detener PostgreSQL depende de quién lo levantó.** Si lo levantó el
  instalador con Docker: `docker compose down` (`-v` borra también el volumen de
  datos). Si ya estaba corriendo: `sudo systemctl stop postgresql`, o lo que
  usaste para arrancarlo. El instalador te dice cuál corresponde en vez de
  asumir siempre Docker.
- Si usás Docker, PostgreSQL corre con `restart: unless-stopped` (siempre activo)
- La base se resuelve por **puerto**: sale de `LEMORIA_DB_PORT` en `.env`.
  Probá `pg_isready -h localhost -p <puerto>` para ver quién responde.
- **Nunca** hay que sumar al usuario al grupo `docker` para que Lemoria
  funcione. Es root sin contraseña. La vía recomendada es PostgreSQL nativo:
  [la advertencia completa](#sobre-sudo-usermod--ag-docker-user).
- Sin `gh` (GitHub CLI) el github-agent usa git manual
- El vault para Obsidian se configura en `.env` (`LEMORIA_VAULT_PATH`) y por
  defecto queda en `~/.lemoria/vault`, **fuera de cualquier repositorio git**.
  Contiene memoria privada (conversaciones, ADRs, PRDs), así que no debería
  terminar nunca en un commit. Si lo apontas dentro de un repo, Lemoria lo
  agrega solo al `.gitignore` de ese repo.
