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
- **PostgreSQL** >= 14 — o Docker con Docker Compose, si no tienes uno
- **OpenCode** (CLI)
- **Obsidian** (opcional)
- **GitHub CLI `gh`** (opcional, para PRs automáticos)

Docker **no** es obligatorio. Si ya tenés un PostgreSQL corriendo (en Arch es lo
normal), el instalador lo detecta y lo deja como está: no administra servidores
que ya estaban andando. Si no hay ninguno, lo levanta con Docker.

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
| 1 | Verifica Python y cómo arrives a PostgreSQL (nativo o Docker) |
| 2 | Crea `.env` |
| 3 | Verifica las credenciales, o levanta PostgreSQL en Docker si no hay ninguno |
| 4 | Instala `lemoria` como comando global (`pip install --user`, con venv propio como alternativa) |
| 5 | Inicializa la base de datos |
| 6 | Copia agentes y skills a `~/.config/opencode/`, con `default_agent: orchestrator` |
| 7 | Configura Context7 MCP (documentación en tiempo real para librerías) |
| 8 | Detecta tu entorno: registra los agentes, ofrece el panel de Omarchy y avisa si no hay opencode |
| 9 | Resumen con lo que quedó instalado |

El paso 8 es el que decide integrations según la máquina: el panel de Omarchy
solo se ofrece si estás en Omarchy, y la telemetría solo se activa si existe un
`opencode.db`. Ninguna de las dos es obligatoria para instalar Lemoria.

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

- Si usás Docker, PostgreSQL corre con `restart: unless-stopped` (siempre activo)
- Sin `gh` (GitHub CLI) el github-agent usa git manual
- El vault para Obsidian se configura en `.env` (`LEMORIA_VAULT_PATH`) y por
  defecto queda en `~/.lemoria/vault`, **fuera de cualquier repositorio git**.
  Contiene memoria privada (conversaciones, ADRs, PRDs), así que no debería
  terminar nunca en un commit. Si lo apontas dentro de un repo, Lemoria lo
  agrega solo al `.gitignore` de ese repo.
